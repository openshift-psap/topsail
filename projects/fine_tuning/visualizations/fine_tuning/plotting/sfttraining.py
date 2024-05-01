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
    SFTTraining()


def generateSFTTrainingData(entries, _variables, _ordered_vars, sfttraining_key):
    data = []

    for entry in entries:
        datum = dict()
        try:
            datum["gpu"] = entry.settings.gpu
        except AttributeError:
            datum["gpu"] = 1

        datum[sfttraining_key] = getattr(entry.results.sft_training_metrics, sfttraining_key, 0)

        data.append(datum)

    return data


class SFTTraining():
    def __init__(self):
        self.name = "SFTTraining"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        cfg__sft_key = cfg.get("sfttraining_key", False)

        if not cfg__sft_key:
            raise ValueError("'sfttraining_key' is a mandatory parameter ...")

        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateSFTTrainingData(entries, variables, ordered_vars, cfg__sft_key))

        if df.empty:
            return None, "Not data available ..."

        x_key = "gpu"
        df = df.sort_values(by=[x_key], ascending=False)

        y_name = "Time Per Output Token"
        y_unit = "ms/token"
        y_key = cfg__sft_key

        fig = px.line(df, hover_data=df.columns, x=x_key, y=y_key)


        for i in range(len(fig.data)):
            fig.data[i].update(mode='lines+markers+text')

        fig.update_xaxes(title="Number of GPUs used for the fine-tuning")

        #fig.update_yaxes(title=f"❮ Mean {y_name} (in {y_unit})<br>Lower is better")
        fig.update_layout(title=cfg__sft_key, title_x=0.5,)
        #fig.update_layout(legend_title_text="Model name")

        # ❯ or ❮

        return fig, ""
