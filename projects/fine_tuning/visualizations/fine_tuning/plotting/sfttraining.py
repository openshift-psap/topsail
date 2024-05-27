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


def generateSFTTrainingData(entries, x_key, _variables, sfttraining_key, compute_speedup=False):
    data = []


    variables = [v for v in _variables if v != x_key]
    if not variables and x_key != "gpu":
        variables += [x_key]

    for entry in entries:
        datum = dict()
        if x_key == "gpu":
            datum[x_key] = entry.results.allocated_resources.gpu
        else:
            datum[x_key] = entry.settings.__dict__[x_key]

        datum[sfttraining_key] = getattr(entry.results.sft_training_metrics, sfttraining_key, 0)

        datum["name"] = entry.get_name(variables)

        data.append(datum)

    if not compute_speedup:
        return data, None

    ref = None
    for datum in data:
        if datum[x_key] == 1:
            ref = datum[sfttraining_key]

    if not ref:
        return data, None

    for datum in data:
        datum[f"{sfttraining_key}_speedup"] = speedup = ref / datum[sfttraining_key]
        datum[f"{sfttraining_key}_efficiency"] = speedup / datum[x_key]

    return data, ref


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
        cfg__speedup = cfg.get("speedup", False)
        cfg__efficiency = cfg.get("efficiency", False)

        from ..store import parsers
        key_properties = parsers.SFT_TRAINER_RESULTS_KEYS[cfg__sft_key]

        if not cfg__sft_key:
            raise ValueError("'sfttraining_key' is a mandatory parameter ...")

        entries = common.Matrix.all_records(settings, setting_lists)

        has_gpu = "gpu" in ordered_vars
        x_key = "gpu" if has_gpu else (ordered_vars[0] if ordered_vars else "expe")

        compute_speedup = has_gpu

        data, has_speedup = generateSFTTrainingData(entries, x_key, variables, cfg__sft_key, compute_speedup)
        df = pd.DataFrame(data)

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=[x_key], ascending=False)

        y_key = cfg__sft_key
        if (cfg__speedup or cfg__efficiency) and not has_speedup:
            return None, "Cannot compute the speedup & efficiency (reference value not found)"

        if cfg__speedup:
            y_key += "_speedup"
        elif cfg__efficiency:
            y_key += "_efficiency"

        if has_gpu or has_speedup:
            fig = px.line(df, hover_data=df.columns, x=x_key, y=y_key, color="name")

            for i in range(len(fig.data)):
                fig.data[i].update(mode='lines+markers+text')
                fig.update_yaxes(rangemode='tozero')
        else:
            fig = px.bar(df, hover_data=df.columns, x=x_key, y=y_key, color="name")

        if has_gpu:
            fig.update_xaxes(title="Number of GPUs used for the fine-tuning")
        else:
            fig.update_xaxes(title=x_key)

        y_title = getattr(key_properties, "title", "speed")
        y_units = key_properties.units

        if cfg__speedup:
            what = " speedup"
            y_lower_better = False
        elif cfg__efficiency:
            what = " efficiency"
            y_lower_better = False
        else:
            y_lower_better = key_properties.lower_better
            what = f", in {y_units}"

        y_title = f"Fine-tuning {y_title}{what}. "
        title = y_title + "<br>"+("Lower is better" if y_lower_better else "Higher is better")
        fig.update_yaxes(title=("❮ " if y_lower_better else "") + y_title + (" ❯" if not y_lower_better else ""))
        fig.update_layout(title=title, title_x=0.5,)
        fig.update_layout(legend_title_text="Configuration")

        # ❯ or ❮

        msg = []
        min_row_idx = df.idxmin()[y_key]
        max_row_idx = df.idxmax()[y_key]

        min_count = df['gpu' if has_gpu else 'name'][min_row_idx]
        max_count = df['gpu' if has_gpu else 'name'][max_row_idx]

        if has_gpu:
            min_name = f"{min_count} GPU" + "s" if min_count > 1 else ""
            max_name = f"{max_count} GPU" + "s" if max_count > 1 else ""
        else:
            min_name = f"{x_key}={min_count}"
            max_name = f"{x_key}={max_count}"

        if cfg__efficiency:
            units = ""
        elif cfg__speedup:
            units = "x"
        else:
            units = y_units

        if len(data) > 1:
            msg.append(f"Max: {df[y_key][max_row_idx]:.2f} {units} ({max_name}, "+ ("slowest" if y_lower_better else "fastest") +")")
            msg.append(html.Br())
            msg.append(f"Min: {df[y_key][min_row_idx]:.2f} {units} ({min_name}, "+ ("fastest" if y_lower_better else "slowest") +")")

        return fig, msg
