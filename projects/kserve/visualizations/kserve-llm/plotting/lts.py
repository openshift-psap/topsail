from collections import defaultdict
import re
import logging
import datetime
import math
import copy

import statistics as stats

import plotly.subplots
import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import error_report, report

def register():
    LtsThrougput()
    LtsLatencyPerToken()
    LtsModelLoadTime()


def generateTimePerOutputTokenStats(time_per_output_token):
    stats_dict = {}

    stats_dict["tpot.min"] = time_per_output_token["min"]
    stats_dict["tpot.max"] = time_per_output_token["max"]

    stats_dict["tpot.90%"] = time_per_output_token["percentile_90"]
    stats_dict["tpot.95%"] = time_per_output_token["percentile_95"]

    stats_dict["tpot.med"] = time_per_output_token["median"]
    return stats_dict


def generateLtsData(entries, _variables):
    data = []
    for entry in entries:
        datum = dict(name=entry.get_name(_variables),)

        datum["throughput"] = entry.results.lts.results.throughput
        datum |= generateTimePerOutputTokenStats(entry.results.lts.results.time_per_output_token)
        try:
            datum["model_load_time"] = entry.results.lts.results.model_load_duration
        except AttributeError:
            datum["model_load_time"] = None
        data.append(datum)

    return data


class LtsThrougput():
    def __init__(self):
        self.name = "LTS: Throughput"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateLtsData(entries, variables))

        if df.empty:
            return None, "Not data available ..."
        fig = px.line(df, hover_data=df.columns, x="name", y="throughput", markers=True)
        fig.data[0].name = "Throughput"
        fig.data[0].showlegend = True

        list(map(fig.add_trace, get_regression_lanes("throughput", df.name, df.throughput, default_op="max")))

        fig.update_layout(title=f"Throughput the load tests", title_x=0.5,)
        fig.update_yaxes(title=f"Throughput (in tokens/s) ❯")
        fig.update_xaxes(title=f"")

        return fig, ""


class LtsLatencyPerToken():
    def __init__(self):
        self.name = "LTS: Time Per Output Token"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateLtsData(entries, variables))

        if df.empty:
            return None, "Not data available ..."
        fig = px.line(df, hover_data=df.columns, x="name", y="tpot.med", markers=True)
        fig.data[0].name = "median TPOT"
        fig.data[0].showlegend = True

        list(map(fig.add_trace, get_regression_lanes("median TPOT", df.name, df["tpot.med"], default_op="min")))

        fig.update_layout(title=f"Time Per Output Token of the load tests", title_x=0.5,)
        fig.update_yaxes(title=f"❮ Time Per Output Token (in ms/token)")
        fig.update_xaxes(title=f"")

        return fig, ""


class LtsModelLoadTime():
    def __init__(self):
        self.name = "LTS: Model Load Time"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateLtsData(entries, variables))

        if df.empty:
            return None, "Not data available ..."
        fig = px.line(df, hover_data=df.columns, x="name", y="model_load_time", markers=True)
        fig.data[0].name = "Model load time"
        fig.data[0].showlegend = True

        list(map(fig.add_trace, get_regression_lanes("model load time", df.name, df.model_load_time, default_op="min")))

        fig.update_layout(title=f"Model load times", title_x=0.5,)
        fig.update_yaxes(title=f"❮ Model Load Time (in s)")
        fig.update_xaxes(title=f"")

        return fig, ""


def find_reference_point(df_name, df_colname, default_op):
    for name, value in zip(df_name, df_colname):
        if name.endswith("-GA"):
            return "GA", value

    return default_op, getattr(df_colname, default_op)()


def get_lane(x_col, ref_value, pct, name):
    if ref_value == "max": import pdb;pdb.set_trace()
    new_value = ref_value * (1 + pct/100)

    return go.Scatter(x=x_col,
                      y=[new_value] * len(x_col),
                      name=name,
                      mode="lines",
                      line_dash="dot",
                      )

def get_regression_lanes(y_col_name, x_col, y_col, default_op):
    ref_name, ref_value = find_reference_point(x_col, y_col, default_op)

    diff_pct = [-round((1 - y/ref_value)*100) for y in y_col if not math.isnan(y)]

    ROUND = 5
    round_pcts = set([0, 5, -5] + [ROUND * round(pct/ROUND) for pct in diff_pct])

    for pct in sorted(round_pcts):
        name = f"{ref_name} {y_col_name}" if pct == 0 else \
            f"{pct:+d}% of the {ref_name} {y_col_name}"

        yield get_lane(x_col, ref_value, pct, name)
