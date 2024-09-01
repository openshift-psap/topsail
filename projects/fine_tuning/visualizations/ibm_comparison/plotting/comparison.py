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


METRICS = {
    "train_tokens_per_second": {
        "title": "Train Tokens per Second for Different GPU and Batch Size Settings",
        "label": "Train Tokens per Second",
        "lower_better": False,
        "same_as": "dataset_tokens_per_second",
    },
    "train_tokens_per_gpu_per_second": {
        "title": "Train Tokens per GPU per Second for Different GPU and Batch Size Settings",
        "label": "Train Tokens per GPU per Second",
        "lower_better": False,
        "same_as": "dataset_tokens_per_gpu_per_second",
    },
    "train_samples_per_second": {
        "title": "Train Samples per Second for Different GPU and Batch Size Settings",
        "label": "Train Samples per Second",
        "lower_better": False,
        "same_as": None,
    },
    "train_runtime": {
        "title": "Train Runtime for Different GPU and Batch Size Settings",
        "label": "Train Runtime",
        "lower_better": True,
        "same_as": None,
    },
    "train_steps_per_second": {
        "title": "Train Steps per Second for Different GPU and Batch Size Settings",
        "label": "Train Steps per Second",
        "lower_better": False,
        "same_as": None,
    },
}

def register():
    Comparison()


def generateComparisonData(entries, x_key, variables, metric_name):
    data = []

    for entry in entries:
        data.append(dict(
            name=entry.get_name([v for v in variables if v is not x_key]),
        ))
        data[-1][x_key] = entry.results.data.get(x_key)
        data[-1][metric_name] = entry.results.data.get(metric_name)

    return data


class Comparison():
    def __init__(self):
        self.name = "Comparison"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        cfg__metric_name = cfg.get("metric_name", None)
        if cfg__metric_name is None:
            return None, f"metric_name config is missing :/ {', '.join(METRICS)}"

        cfg__model_name = cfg.get("model_name", None)
        if cfg__model_name is None:
            if "model_name" in variables:
                return None, "model_name must be defined :/"
            cfg__model_name = settings["model_name"]

        for x_key in ordered_vars:
            if not isinstance(variables[x_key][0], str):
                break
        else:
            return None, "No numeric variable found ..."

        # x_key is set

        data = generateComparisonData(common.Matrix.all_records(settings, setting_lists), x_key, variables, cfg__metric_name)
        df = pd.DataFrame(data)

        if df.empty:
            return None, "Nothing to plot"

        fig = px.line(df, hover_data=df.columns, x=x_key, y=cfg__metric_name, color="name")
        for i in range(len(fig.data)):
            fig.data[i].update(mode='markers+lines')

        fig.update_yaxes(title=cfg__metric_name, range=[0, df[cfg__metric_name].max()*1.1])
        fig.update_xaxes(title=x_key, range=[0, df[x_key].max()*1.1])

        subtitle = " ".join([f"{k}={v}" for k, v in settings.items() if k not in list(variables.keys()) + ["stats"]])
        title = f"<b>{cfg__metric_name}</b><br>{subtitle}"

        fig.update_layout(title=title, title_x=0.5,)
        fig.update_layout(legend_title_text="Configuration")

        # ❯ or ❮

        msg = []

        return fig, msg
