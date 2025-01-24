from collections import defaultdict
import re
import logging
import datetime
import math
import copy
import numbers
import numpy
import statistics as stats
import matrix_benchmarking.store as store

import plotly.subplots
import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common
import matrix_benchmarking.analyze.report as analyze_report

import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report


def register():
    KpiPlot()
    KpiPlotReport()


def generateData(entries, x_key, kpi_name,_variables, filter_key=None, filter_value=None):
    data = []

    variables = dict(_variables)
    properties = None

    if x_key in variables:
        del variables[x_key]

    for entry in entries:
        if filter_key is not None and entry.get_settings()[filter_key] != filter_value:
            continue

        datum = dict()
        datum[x_key] = entry.settings.__dict__[x_key] \
            if x_key else None

        kpi = entry.results.lts.kpis[kpi_name]
        if not properties:
            properties = dict(
                unit = kpi.divisor_unit if "divisor" in kpi.__dict__ else kpi.unit,
                title = kpi.help,
                type = kpi.unit,
            )

        value = kpi.value
        if kpi.__dict__.get("divisor"):
            if isinstance(value, list):
                value = [v/kpi.divisor for v in value]
            else:
                value /= kpi.divisor

        text = analyze_report.format_kpi_value(kpi)

        datum["y"] = value
        datum["text"] = text
        datum["name"] = entry.get_name(variables).replace("hyper_parameters.", "")

        if "list" in kpi.unit:
            for v in value:
                datum["y"] = v
                data.append(datum.copy())
        else:
            data.append(datum)

    return data, properties


class KpiPlot():
    def __init__(self):
        self.name = "KPI Plot"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        cfg__filter_key = cfg.get("filter_key", None)
        cfg__filter_value = cfg.get("filter_value", False)
        cfg__kpi_name = cfg.get("kpi_name", None)

        if not cfg__kpi_name:
            return None, "No KPI name passed as parameter ..."

        entries = common.Matrix.all_records(settings, setting_lists)

        has_gpu = "gpu" in ordered_vars and cfg__filter_key != "gpu"

        x_key = "gpu" if has_gpu else (ordered_vars[0] if ordered_vars else None)

        data, properties = generateData(entries, x_key, cfg__kpi_name, variables, cfg__filter_key, cfg__filter_value)

        if not properties:
            return None, "KPI not found ..."

        df = pd.DataFrame(data)
        if df.empty:
            return None, "No data available ..."

        if x_key:
            df = df.sort_values(by=[x_key], ascending=True)

        y_title = properties["title"]
        y_units = properties["unit"]

        is_list_kpi = "list" in properties["type"]

        y_key = "y"
        if has_gpu:
            do_line_plot = True
        elif len(variables) == 1:
            do_line_plot = all(isinstance(v, numbers.Number) for v in list(variables.values())[0])
        elif x_key is None:
            do_line_plot = False
        elif x_key.startswith("hyper_parameters."):
            do_line_plot = True
        elif is_list_kpi:
            do_line_plot = True
        else:
            do_line_plot = False

        text = None if len(variables) > 3 else "text"
        if do_line_plot:
            color = None if (len(variables) == 1) else "name"

            fig = px.line(df, hover_data=df.columns, x=x_key, y=y_key, color=color, text=text)

            for i in range(len(fig.data)):
                if is_list_kpi:
                    fig.data[i].update(mode='markers')
                else:
                    fig.data[i].update(mode='lines+markers+text')

                fig.update_yaxes(rangemode='tozero')

            fig.update_traces(textposition='top center')

        else:
            df = df.sort_values(by=["name"], ascending=True)
            fig = px.bar(df, hover_data=df.columns, x=x_key, y=y_key, color="name", barmode='group', text=text)

        if has_gpu:
            fig.update_xaxes(title="Number of GPUs used for the fine-tuning")
        else:
            fig.update_xaxes(title=x_key)

        x_name = x_key.replace("hyper_parameters.", "") if x_key else "single expe"

        y_lower_better = True
        what = f", in {y_units}"

        y_title = f"Fine-tuning {y_title}{what}. "
        title = y_title + "<br>"+("Lower is better" if y_lower_better else "Higher is better")
        if is_list_kpi:
            title += " (list KPI)"
        fig.update_yaxes(title=("❮ " if y_lower_better else "") + y_title + (" ❯" if not y_lower_better else ""))
        fig.update_layout(title=title, title_x=0.5,)
        fig.update_layout(legend_title_text="Configuration")

        if len(variables) == 1:
            fig.layout.update(showlegend=False)
        fig.update_xaxes(title=x_name)
        # ❯ or ❮
        msg = []

        return fig, msg


class KpiPlotReport():
    def __init__(self):
        self.name = "report: KPI Plot Report"
        self.id_name = self.name
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []

        header += [html.P("These plots show a summary of the Prometheus metrics")]
        header += [html.H2("KPI Plot Report")]

        ordered_vars, settings, _setting_lists, variables, cfg = args
        setting_lists = copy.deepcopy(_setting_lists)

        if not common.Matrix.count_records(settings, setting_lists):
            header.append(html.B("No record found ..."))
            return None, header

        first_entry = next(common.Matrix.all_records(settings, setting_lists))

        for kpi_name in first_entry.results.lts.kpis.keys():

            plot_name = "KPI Plot"
            header += [html.H3(f"• {kpi_name}")]

            kpi_args = report.set_config(dict(kpi_name=kpi_name), args)
            for _ in range(len(ordered_vars)):
                first_var = ordered_vars[0]
                header += [html.H3(f"by {first_var}")]
                header += report.Plot_and_Text(f"KPI Plot", kpi_args)
                ordered_vars.append(ordered_vars.pop(0))

        return None, header
