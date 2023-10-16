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

from . import error_report

def register():
    LatencyDistribution()
    LatencyDetails()
    ErrorDistribution()
    FinishReasonDistribution()


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
        df = pd.DataFrame(generateLatencyDetailsData(entries, variables, only_tokens=cfg__only_tokens))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["timestamp"])
        if cfg__only_tokens:
            y_key = "tokens"
        else:
            y_key = "latencyPerToken"
        fig = px.box(df, hover_data=df.columns,
                      x="model_name", y=y_key, color="test_name")

        fig.update_layout(barmode='stack')
        fig.update_yaxes(range=[0, df[y_key].max() * 1.1])
        if cfg__only_tokens:
            fig.update_layout(title=f"Distribution of the number of tokens of the model answers", title_x=0.5,)
            fig.update_yaxes(title=f"Number of tokens")
        else:
            fig.update_layout(title=f"Distribution of the latency/token of the model answers", title_x=0.5,)
            fig.update_yaxes(title=f"Latency per token (in ms/token)")
        fig.update_xaxes(title=f"Timeline")

        if len(variables) == 1 and "model_name" in variables:
            fig.layout.update(showlegend=False)

        show_message = True
        msg = []
        for test_name in df.test_name.unique():
            stats_data = df[df.test_name == test_name][y_key]

            msg += [html.H3(test_name)]
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


def generateLatencyDetailsData(entries, variables, only_errors=False, test_name_by_error=False, latency_per_token=True, show_errors=False, only_tokens=False):
    data = []
    for entry in entries:
        llm_data = entry.results.llm_load_test_output
        for idx, block in enumerate(llm_data):
            for detail in block["details"]:
                if only_errors and not detail.get("error"):
                    continue # in this plot, ignore the latency if no error occured
                if not show_errors and detail.get("error"):
                    continue

                datum = {}
                datum["index"] = idx
                datum["timestamp"] = detail["timestamp"]

                generatedTokens = int(detail["response"].get("generatedTokens", 1))
                if only_tokens:
                    datum["tokens"] = generatedTokens

                elif latency_per_token:
                    datum["latencyPerToken"] = detail["latency"] / 1000 / 1000 / generatedTokens # in ms/token

                else:
                    datum["latency"] = detail["latency"] / 1000 / 1000

                datum["model_name"] = entry.settings.model_name

                if test_name_by_error:
                    datum["test_name"] = error_report.simplify_error(detail.get("error"))
                elif detail.get("error"):
                    datum["test_name"] = "errors"
                else:
                    datum["test_name"] = entry.get_name(variables).replace(", ", "<br>")

                if only_errors:
                    datum["error"] = detail.get("error")

                data.append(datum)

    return data


def generateErrorHistogramData(entries, variables):
    data = []

    for entry in entries:
        llm_data = entry.results.llm_load_test_output

        errorDistribution = defaultdict(int)
        for idx, block in enumerate(llm_data):
            for descr, count in block.get("errorDistribution", {}).items():
                errorDistribution[error_report.simplify_error(descr)] += count

        for descr, count in errorDistribution.items():
            datum = {}
            datum["error"] = descr
            datum["count"] = count
            datum["test_name"] = entry.get_name(variables).replace(", ", "<br>")
            data.append(datum)

    return data


def generateFinishReasonData(entries, variables):
    data = []

    for entry in entries:
        llm_data = entry.results.llm_load_test_output

        finishReasons = defaultdict(int)
        for idx, block in enumerate(llm_data):
            for detail in block.get("details"):
                if detail["error"]:
                    reason = "ERROR"
                else:
                    reason = detail["response"].get("finishReason", "ERROR")
                pass
                finishReasons[reason] += 1

        for reason, count in finishReasons.items():
            datum = {}
            datum["reason"] = reason
            datum["count"] = count
            datum["test_name"] = entry.get_name(variables).replace(", ", "<br>")
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

        df = df.sort_values(by=["timestamp"])

        if cfg__only_tokens:
            y_key = "tokens"
        elif latency_per_token:
            y_key = "latencyPerToken"
        else:
            y_key = "latency"

        fig = px.line(df, hover_data=df.columns,
                      x="timestamp", y=y_key, color="test_name")


        for i in range(len(fig.data)):
            fig.data[i].update(mode='markers')

        fig.update_layout(barmode='stack')
        fig.update_yaxes(range=[0, df[y_key].max() * 1.1])
        subtitle = f"<br>{cfg__entry.get_name(variables)}" if cfg__entry else ""

        fig.update_xaxes(title=f"Timeline")
        if cfg__only_tokens:
            fig.update_yaxes(title=f"Number of tokens in the answer")
            fig.update_layout(title=f"Detailed token count of the model answers{subtitle}", title_x=0.5,)
        elif latency_per_token:
            fig.update_yaxes(title=f"Latency per token (in ms/token)")
            fig.update_layout(title=f"Detailed latency/token of {'errors of ' if cfg__only_errors else ''}the load test{subtitle}", title_x=0.5,)
        else:
            fig.update_yaxes(title=f"Latency (in ms)")
            fig.update_layout(title=f"Detailed latency of {'errors of ' if cfg__only_errors else ''}the load test{subtitle}", title_x=0.5,)

        if cfg__only_errors:
            fig.update_layout(legend=dict(yanchor="top",
                                          y=-0.1,
                                          xanchor="left",
                                          x=0.01))

        if cfg__entry:
            fig.layout.update(showlegend=False)

        return fig, ""


class ErrorDistribution():
    def __init__(self):
        self.name = "Errors distribution"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateErrorHistogramData(entries, variables))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["test_name"])

        fig = px.bar(df, hover_data=df.columns,
                     x="test_name", y="count", color="error")


        fig.update_layout(title=f"Distribution of the load test errors", title_x=0.5,)

        fig.update_yaxes(title=f"Error occurence count")

        fig.update_layout(legend=dict(yanchor="top",
                                      y=1.55,
                                      xanchor="left",
                                      x=-0.05))

        return fig, ""


class FinishReasonDistribution():
    def __init__(self):
        self.name = "Finish Reason distribution"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateFinishReasonData(entries, variables))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["test_name"])

        fig = px.bar(df, hover_data=df.columns,
                     x="test_name", y="count", color="reason")


        fig.update_layout(title=f"Distribution of the finish reasons", title_x=0.5,)

        fig.update_yaxes(title=f"Finish reason count")

        fig.update_layout(legend=dict(yanchor="top",
                                      y=1.55,
                                      xanchor="left",
                                      x=-0.05))

        return fig, ""
