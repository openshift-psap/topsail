from collections import defaultdict
import re
import logging
import datetime
import math
import copy

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import error_report

def register():
    Latency()
    LatencyDetails()
    ErrorDistribution()


class Latency():
    def __init__(self):
        self.name = "Latency"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        entries = common.Matrix.all_records(settings, setting_lists)
        df = pd.DataFrame(generateLatencyDetailsData(entries, variables))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["timestamp"])

        fig = px.box(df, hover_data=df.columns,
                      x="model_name", y="latencyPerToken", color="test_name")

        fig.update_layout(barmode='stack')
        fig.update_yaxes(range=[0, df.latencyPerToken.max() * 1.1])
        fig.update_layout(title=f"Average latency/token of the models", title_x=0.5,)
        fig.update_xaxes(title=f"Timeline")
        fig.update_yaxes(title=f"Latency per token (in ms/token)")

        return fig, ""


def generateLatencyDetailsData(entries, variables, only_errors=False, test_name_by_error=False, latency_per_token=True, show_errors=False):
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

                if latency_per_token:
                    datum["latencyPerToken"] = detail["latency"] / 1000 / 1000 / detail["response"].get("generatedTokens", 1) # in ms/token

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
        cfg__only_errors = cfg.get("only_errors", False)
        cfg__show_errors = cfg.get("show_errors", cfg__only_errors)

        entries = [cfg__entry] if cfg__entry else \
            common.Matrix.all_records(settings, setting_lists)
        latency_per_token = (not cfg__only_errors and not cfg__show_errors)
        df = pd.DataFrame(generateLatencyDetailsData(entries, variables,
                                                     test_name_by_error=cfg__only_errors,
                                                     show_errors=cfg__show_errors,
                                                     only_errors=cfg__only_errors,
                                                     latency_per_token=latency_per_token))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["timestamp"])

        y_key = "latencyPerToken" if latency_per_token else "latency"
        fig = px.line(df, hover_data=df.columns,
                      x="timestamp", y=y_key, color="test_name")


        for i in range(len(fig.data)):
            fig.data[i].update(mode='markers')

        fig.update_layout(barmode='stack')
        fig.update_yaxes(range=[0, df[y_key].max() * 1.1])
        subtitle = f"<br>{cfg__entry.get_name(variables)}" if cfg__entry else ""

        fig.update_xaxes(title=f"Timeline")
        if latency_per_token:
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
