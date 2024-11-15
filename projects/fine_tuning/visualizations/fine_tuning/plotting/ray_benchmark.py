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

from . import error_report, report

def register():
    RayBenchmarkSummary()
    RayBenchmarkProgress()


def generateRaySummaryData(entries, x_key, y_key, _variables):
    data = []

    variables = [v for v in _variables if v != x_key]
    if not variables and x_key != "gpu" and x_key is not None:
        variables += [x_key]


    for entry in entries:
        datum = dict()


        datum[x_key] = entry.settings.__dict__[x_key] if x_key is not None \
                else "Single entry"

        datum[y_key] = getattr(entry.results.ray_metrics.summary, y_key)
        datum["name"] = entry.get_name(variables).replace("hyper_parameters.", "")

        data.append(datum)

    return data



class RayBenchmarkSummary():
    def __init__(self):
        self.name = "Ray Benchmark Summary"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        from ..store import parsers

        entries = common.Matrix.all_records(settings, setting_lists)

        x_key = ordered_vars[0] if ordered_vars else None
        y_key = "time"
        data = generateRaySummaryData(entries, x_key, y_key, variables)

        df = pd.DataFrame(data)

        if df.empty:
            return None, "Not data available ..."

        if x_key is not None:
            df = df.sort_values(by=[x_key], ascending=False)

        color = None if (len(variables) == 1 and not has_speedup) else "name"
        fig = px.line(df, hover_data=df.columns, x=x_key, y=y_key, color=color)

        for i in range(len(fig.data)):
            fig.data[i].update(mode='lines+markers')
            fig.update_yaxes(rangemode='tozero')

        # ❯ or ❮

        msg = []

        return fig, msg


def generateRayProgressData(entries, x_key, variables, progress_key):
    data = []

    for entry in entries:
        progress_entries = entry.results.sfttrainer_metrics.progress
        entry_name = entry.get_name(variables)

        for progress in progress_entries:
            datum = dict()
            datum[x_key] = getattr(progress, x_key)
            datum[progress_key] = getattr(progress, progress_key, None)
            datum["name"] = entry_name
            data.append(datum)

    return data


class RayBenchmarkProgress():
    def __init__(self):
        self.name = "Ray Benchmark Progress"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        cfg__progress_key = cfg.get("progress_key", False)

        if not cfg__progress_key:
            raise ValueError("'progress_key' is a mandatory parameter ...")

        from ..store import parsers
        progress_key_properties = parsers.SFT_TRAINER_PROGRESS_KEYS[cfg__progress_key]

        entries = common.Matrix.all_records(settings, setting_lists)

        x_key = "epoch"

        data = generateSFTTrainerProgressData(entries, x_key, variables, cfg__progress_key)
        df = pd.DataFrame(data)

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=[x_key], ascending=False)

        y_key = cfg__progress_key
        y_lower_better = progress_key_properties.lower_better

        fig = px.line(df, hover_data=df.columns, x=x_key, y=y_key, color="name")

        for i in range(len(fig.data)):
            fig.data[i].update(mode='lines+markers+text')
            fig.update_yaxes(rangemode='tozero')

        fig.update_xaxes(title="epochs")

        y_title = f"Training {y_key}. "
        title = f"Fine-tuning '{y_key}' progress over the training {x_key}s"
        title += "<br>"+("Lower is better" if y_lower_better else "Higher is better")
        y_title += ("Lower is better" if y_lower_better else "Higher is better")
        fig.update_yaxes(title=("❮ " if y_lower_better else "") + y_title + (" ❯" if not y_lower_better else ""))
        fig.update_layout(title=title, title_x=0.5)
        fig.update_layout(legend_title_text="Configuration")

        return fig, ""
