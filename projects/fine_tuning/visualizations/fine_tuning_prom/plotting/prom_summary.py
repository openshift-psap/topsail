from collections import defaultdict
import re
import logging
import datetime
import math
import copy
import numbers
import numpy
import statistics as stats

import plotly.subplots
import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import report

def register():
    GPUTotalMemoryUsage()
    PromSummaryReport()
    PromSummaryByModelReport()


def generatePromSummaryData(entries, x_key, metric_name, _variables, filter_key=None, filter_value=None):
    data = []

    variables = dict(_variables)

    if x_key in variables:
        del variables[x_key]

    for entry in entries:
        if filter_key is not None and entry.get_settings()[filter_key] != filter_value:
            continue

        datum = dict()
        datum[x_key] = entry.settings.__dict__[x_key]

        metrics = entry.results.metrics["sutest"][metric_name]
        max_val = 0

        for metric in metrics:
            for ts, val in metric.values.items():
                max_val = max(max_val, val)

        datum["y"] = max_val / 1024

        datum["name"] = entry.get_name(variables).replace("hyper_parameters.", "")

        datum["text"] = "{:.2f}".format(datum["y"]) if datum["y"] is not None else "None"

        data.append(datum)

    return data


class GPUTotalMemoryUsage():
    def __init__(self):
        self.name = "Prom Summary: GPU Total Memory Usage"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        cfg__filter_key = cfg.get("filter_key", None)
        cfg__filter_value = cfg.get("filter_value", False)

        entries = common.Matrix.all_records(settings, setting_lists)

        has_gpu = "gpu" in ordered_vars and cfg__filter_key != "gpu"

        x_key = "gpu" if has_gpu else (ordered_vars[0] if ordered_vars else "expe")

        metric_name = "Sutest GPU memory used (all GPUs)"
        y_title = "GPU memory usage (all the GPUs)"
        y_units = "in Gi"

        data = generatePromSummaryData(entries, x_key, metric_name, variables, cfg__filter_key, cfg__filter_value)
        df = pd.DataFrame(data)

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=[x_key], ascending=False)

        y_key = "y"
        if has_gpu:
            do_line_plot = True

        elif len(variables) == 1:
            do_line_plot = all(isinstance(v, numbers.Number) for v in list(variables.values())[0])
        elif x_key.startswith("hyper_parameters."):
            do_line_plot = True
        else:
            do_line_plot = False

        text = None if len(variables) > 3 else "text"
        if do_line_plot:
            color = None if (len(variables) == 1) else "name"

            fig = px.line(df, hover_data=df.columns, x=x_key, y=y_key, color=color, text=text)

            for i in range(len(fig.data)):
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

        x_name = x_key.replace("hyper_parameters.", "")

        y_lower_better = True
        what = f", in {y_units}"

        y_title = f"Fine-tuning {y_title}{what}. "
        title = y_title + "<br>"+("Lower is better" if y_lower_better else "Higher is better")

        fig.update_yaxes(title=("❮ " if y_lower_better else "") + y_title + (" ❯" if not y_lower_better else ""))
        fig.update_layout(title=title, title_x=0.5,)
        fig.update_layout(legend_title_text="Configuration")

        if len(variables) == 1:
            fig.layout.update(showlegend=False)
        fig.update_xaxes(title=x_name)
        # ❯ or ❮
        msg = []

        return fig, msg


class PromSummaryReport():
    def __init__(self):
        self.name = "report: Prometheus Summary Report"
        self.id_name = self.name.lower().replace("/", "-")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []

        header += [html.P("These plots show a summary of the Prometheus metrics")]

        header += [html.H2("GPU Usage")]

        plot_name = "GPU Total Memory Usage"
        header += [html.H3(plot_name)]

        ordered_vars, settings, _setting_lists, variables, cfg = args

        setting_lists = copy.deepcopy(_setting_lists)

        for _ in range(len(ordered_vars)):
            first_var = ordered_vars[0]
            header += [html.H3(f"by {first_var}")]
            header += report.Plot_and_Text(f"Prom Summary: {plot_name}", args)
            ordered_vars.append(ordered_vars.pop(0))

        if "gpu" in variables:
            gpu_counts = variables.pop("gpu")
            ordered_vars.remove("gpu")
        else:
            gpu_counts = [None]

        header += [html.H2("GPU Usage, by GPU count")]

        for gpu_count in gpu_counts:
            if gpu_count is not None:
                header += [html.H4(f"with {gpu_count} GPU{'s' if gpu_count > 1 else ''} per job")]

            _setting_lists[:] = []

            for settings_group in setting_lists:
                current_group = []
                for (k, v) in settings_group:
                    if k == "gpu" and v != gpu_count: continue
                    current_group.append((k, v, ))
                if current_group:
                    _setting_lists.append(current_group)

            header += report.Plot_and_Text(f"Prom Summary: {plot_name}", args)

        return None, header


class PromSummaryByModelReport():
    def __init__(self):
        self.name = "report: Prometheus Summary By Model Report"
        self.id_name = self.name.lower().replace("/", "-")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, _setting_lists, variables, cfg = args

        header = []

        setting_lists = copy.deepcopy(_setting_lists)
        header += [html.P("These plots show a summary of the Prometheus metrics")]

        if "gpu" in variables:
            gpu_counts = variables.pop("gpu")
            ordered_vars.remove("gpu")
        else:
            gpu_counts = [None]

        model_names = variables.get("model_name", [])
        if model_names:
            ordered_vars.remove("model_name")
            variables.pop("model_name")
        else:
            model_names.append(None)

        for model_name in model_names:
            plot_name = "GPU Total Memory Usage"
            header += [html.H3(((model_name + " | ") if model_name else "") + plot_name)]
            for gpu_count in gpu_counts:
                if gpu_count is not None:
                    header += [html.H4(f"with {gpu_count} GPU{'s' if gpu_count > 1 else ''} per job")]

                _setting_lists[:] = []

                for settings_group in setting_lists:
                    current_group = []
                    for (k, v) in settings_group:
                        if k == "model_name" and v != model_name: continue
                        if k == "gpu" and v != gpu_count: continue
                        current_group.append((k, v, ))
                    if current_group:
                        _setting_lists.append(current_group)

                header += report.Plot_and_Text(f"Prom Summary: {plot_name}", args)

        return None, header
