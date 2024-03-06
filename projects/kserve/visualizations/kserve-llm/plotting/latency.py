from collections import defaultdict
import re
import logging
import datetime
import math
import copy

import statistics as stats

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import error_report, report

def register():
    LatencyDistribution()
    LatencyDetails()

class LatencyDistribution():
    def __init__(self):
        self.name = "Latency distribution"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        entries = common.Matrix.all_records(settings, setting_lists)
        cfg__only_tokens = cfg.get("only_tokens", False)
        cfg__collapse_index = cfg.get("collapse_index", False)
        cfg__box_plot = cfg.get("box_plot", True)
        cfg__show_text = cfg.get("show_text", True)

        df = pd.DataFrame(generateLatencyDetailsData(entries, variables, only_tokens=cfg__only_tokens, collapse_index=cfg__collapse_index))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["timestamp"])
        if cfg__only_tokens:
            y_key = "tokens"
        else:
            y_key = "latencyPerToken"

        if cfg__box_plot:
            fig = px.box(df, hover_data=df.columns,
                         x="model_name", y=y_key, color="test_name")
            fig.update_yaxes(range=[0, df[y_key].max() * 1.1])
        else:
            fig = plotCustomComparison(df, x="test_fullname", y=y_key)

        if cfg__only_tokens:
            plot_title = f"Distribution of the number of tokens of the model answers"
            fig.update_yaxes(title=f"Number of tokens")
        else:
            plot_title = f"Distribution of the latency/token of the model answers"
            fig.update_yaxes(title=f"❮ Latency per token (in ms/token)<br>Lower is better")

        if "model_name" not in variables:
            plot_title += f"<br><b>{settings['model_name']}</b>"

        fig.update_layout(title=plot_title, title_x=0.5,)
        fig.update_xaxes(title=f"")
        fig.update_layout(legend_title_text='')

        if len(variables) == 1 and "model_name" in variables:
            fig.layout.update(showlegend=False)

        if cfg__box_plot and cfg__collapse_index:
            fig.layout.update(showlegend=False)

        if not cfg__box_plot:
            for plot in fig.data:
                if plot.name in ["max", "99th percentile"]:
                    plot.visible = "legendonly"

        msg = []
        for test_fullname in df.sort_values(by=["test_fullname"]).test_fullname.unique() if cfg__show_text else []:
            stats_data = df[df.test_fullname == test_fullname][y_key]

            msg += [html.H3(test_fullname)]
            q0 = stats_data.min()
            q100 = stats_data.max()
            q1, med, q3 = stats.quantiles(stats_data)
            q90 = stats.quantiles(stats_data, n=10)[8] # 90th percentile
            if cfg__only_tokens:
                label = "the calls contained less than"
                unit = "tokens"
            else:
                label = "the calls performed faster than"
                unit = "ms/token"

            msg.append(f"0% of {label} {q0:.0f} {unit} [min]")
            msg.append(html.Br())
            msg.append(f"25% of {label} {q1:.0f} {unit} [Q1]")
            msg.append(html.Br())
            msg.append(f"50% of {label} {med:.0f} {unit} (+ {med-q1:.0f} {unit}) [median]")
            msg.append(html.Br())
            msg.append(f"75% of {label} {q3:.0f} {unit} (+ {q3-med:.0f} {unit}) [Q3]")
            msg.append(html.Br())
            msg.append(f"90% of {label} {q90:.0f} {unit} (+ {q90-q3:.0f} {unit}) [90th quantile]")
            msg.append(html.Br())
            msg.append(f"100% of {label} {q100:.0f} {unit} (+ {q100-q90:.0f} {unit}) [max]")
            msg.append(html.Br())
            msg.append(html.Br())
            msg.append(f"There are {len(stats_data)} recorded calls.")
            msg.append(html.Br())
            msg.append(f"The median is {med:.0f} {unit}.")
            msg.append(html.Br())
            q3_q1 = q3 - q1
            msg.append(f"There are {q3_q1:.0f} {unit} between Q1 and Q3 ({q3_q1/med*100:.1f}% of the median).")
            msg.append(html.Br())
            q100_q0 = q100 - q0
            msg.append(f"There are {q100 - q0:.0f} {unit} between min and max ({q100_q0/med*100:.1f}% of the median).")
            msg.append(html.Br())

        return fig, msg


def plotCustomComparison(df, x, y):
    fig = go.Figure()
    data_whatxy = defaultdict(dict)

    for x_value in df[x].unique():
        df_x_value = df[df[x] == x_value]
        y_min = df_x_value[y].min()
        y_max = df_x_value[y].max()
        q1, median, q3 = stats.quantiles(df_x_value[y])

        q90 = stats.quantiles(df_x_value[y], n=10)[8] # 90th percentile
        q99 = stats.quantiles(df_x_value[y], n=100)[98] # 99th percentile

        data_whatxy["max"][x_value] = y_max
        data_whatxy["99th percentile"][x_value] = q99
        data_whatxy["90th percentile"][x_value] = q90
        data_whatxy["Q3 (75%)"][x_value] = q3
        data_whatxy["median (50%)"][x_value] = median
        data_whatxy["Q1 (25%)"][x_value] = q1
        data_whatxy["min"][x_value] = y_min

    all_x_values = set()
    all_y_values = []
    for legend_name, xy_values in data_whatxy.items():
        x_values = list(xy_values.keys())
        y_values = list(xy_values.values())

        all_x_values.update(x_values)
        all_y_values += y_values
        fig.add_trace(go.Bar(x=x_values,
                             y=y_values,
                             name=legend_name,
                             ))
    fig.update_layout(barmode='overlay')

    return fig

def generateLatencyDetailsData(entries, _variables, only_errors=False, test_name_by_error=False, latency_per_token=True, show_errors=False, only_tokens=False, collapse_index=False):
    data = []

    if "mode" in _variables:
        variables = list(_variables) # make a copy before modifying
        variables.remove("mode")
        has_multiple_modes = True
    else:
        variables = _variables
        has_multiple_modes = False

    for entry in entries:
        if not entry.results.llm_load_test_output: continue
        for result in entry.results.llm_load_test_output["results"]:

            if only_errors and not result["error_code"]:
                continue # in this plot, ignore the latency if no error occured
            if not show_errors and result["error_code"]:
                continue

            datum = {}

            datum["timestamp"] = datetime.datetime.fromtimestamp(result["start_time"])

            generatedTokens = result["output_tokens"]
            datum["tokens"] = generatedTokens

            datum["latency"] = result["response_time"]
            datum["latencyPerToken"] = datum["latency"] / generatedTokens # in ms/token

            datum["model_name"] = (f"{entry.settings.model_name}<br>"+entry.get_name([v for v in variables if v not in ("index", "mode", "model_name")]).replace(", ", "<br>")).removesuffix("<br>")

            if has_multiple_modes:
                datum["model_name"] += f"<br>{entry.settings.mode.title()}"

            if collapse_index:
                datum["test_name"] = entry.get_name(v for v in variables if v != "index").replace(", ", "<br>")
            elif test_name_by_error:
                simplified_error = datum["test_name"] = error_report.simplify_error(detail.get("error"))
                if not simplified_error: continue

            elif result["error_code"]:
                datum["test_name"] = "errors"
                datum["latency"] = -1
            else:
                datum["test_name"] = entry.get_name(variables).replace(", ", "<br>")

            datum["error"] = result["error_text"] or "no error"

            datum["test_fullname"] = entry.get_name([v for v in variables if v != "index"] if collapse_index else variables)
            if has_multiple_modes:
                datum["test_fullname"] += f" {entry.settings.mode.title()}"

            data.append(datum)

    return data


class LatencyDetails():
    def __init__(self):
        self.name = "Latency details"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        cfg__entry = cfg.get("entry", None)
        cfg__only_tokens = cfg.get("only_tokens", False)
        cfg__only_errors = cfg.get("only_errors", False)
        cfg__show_errors = cfg.get("show_errors", cfg__only_errors)

        entries = [cfg__entry] if cfg__entry else \
            common.Matrix.all_records(settings, setting_lists)
        latency_per_token = (not cfg__only_errors and not cfg__show_errors)
        df = pd.DataFrame(generateLatencyDetailsData(entries, variables,
                                                     test_name_by_error=cfg__only_errors,
                                                     show_errors=cfg__show_errors,
                                                     only_errors=cfg__only_errors,
                                                     only_tokens=cfg__only_tokens,
                                                     latency_per_token=latency_per_token))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["test_name"])

        if cfg__only_tokens:
            y_key = "tokens"
        elif latency_per_token:
            y_key = "latencyPerToken"
        else:
            y_key = "latency"

        if cfg__only_tokens and cfg__entry:
            color = "latency"
        elif latency_per_token and cfg__entry:
            color = "tokens"
        elif cfg__show_errors:
            color = "tokens"
        else:
            color = "test_name"

        fig = px.scatter(df, hover_data=df.columns,
                      x="timestamp", y=y_key, color=color)

        fig.update_layout(barmode='stack')
        fig.update_yaxes(range=[0, df[y_key].max() * 1.1])
        if cfg__entry:
            subtitle = f"<br>{cfg__entry.get_name(reversed(sorted(set(list(variables.keys()) + ['model_name']))))}"
        elif "model_name" not in variables:
            subtitle = f"<br><b>{settings['model_name']}</b>"
        else:
            subtitle = ""

        fig.update_layout(legend_title_text='')
        fig.update_xaxes(title=f"Timeline")
        if cfg__only_tokens:
            fig.update_yaxes(title=f"Number of tokens in the answer")
            fig.update_layout(title=f"Detailed token count of the model answers{subtitle}", title_x=0.5,)
        elif latency_per_token:
            fig.update_yaxes(title=f"❮ Latency per token (in ms/token)<br>Lower is better")
            fig.update_layout(title=f"Detailed latency/token of {'errors of ' if cfg__only_errors else ''}the load test{subtitle}", title_x=0.5,)
        else:
            fig.update_yaxes(title=f"❮ Latency (in ms)")
            fig.update_layout(title=f"Detailed latency of {'errors of ' if cfg__only_errors else ''}the load test{subtitle}", title_x=0.5,)

        if cfg__only_errors:
            fig.update_layout(legend=dict(yanchor="top",
                                          y=-0.1,
                                          xanchor="left",
                                          x=0.01))

        if cfg__entry and not latency_per_token:
            fig.layout.update(showlegend=False)

        return fig, ""
