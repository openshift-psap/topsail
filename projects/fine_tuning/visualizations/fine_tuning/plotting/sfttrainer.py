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
    SFTTrainerSummary()
    SFTTrainerProgress()


def generateSFTTrainerSummaryData(entries, x_key, _variables, summary_key, compute_speedup=False):
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

        datum[summary_key] = getattr(entry.results.sfttrainer_metrics.summary, summary_key, None)

        datum["name"] = entry.get_name(variables)

        data.append(datum)

    if not compute_speedup:
        return data, None

    ref = None
    for datum in data:
        if datum[x_key] == 1:
            ref = datum[summary_key]

    if not ref:
        return data, None

    for datum in data:
        datum[f"{summary_key}_speedup"] = speedup = ref / datum[summary_key]
        datum[f"{summary_key}_efficiency"] = speedup / datum[x_key]

    return data, ref


class SFTTrainerSummary():
    def __init__(self):
        self.name = "SFTTrainer Summary"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        cfg__summary_key = cfg.get("summary_key", False)
        cfg__speedup = cfg.get("speedup", False)
        cfg__efficiency = cfg.get("efficiency", False)

        from ..store import parsers
        summary_key_properties = parsers.SFT_TRAINER_SUMMARY_KEYS[cfg__summary_key]

        if not cfg__summary_key:
            raise ValueError("'summary_key' is a mandatory parameter ...")

        entries = common.Matrix.all_records(settings, setting_lists)

        has_gpu = "gpu" in ordered_vars
        x_key = "gpu" if has_gpu else (ordered_vars[0] if ordered_vars else "expe")

        compute_speedup = has_gpu

        data, has_speedup = generateSFTTrainerSummaryData(entries, x_key, variables, cfg__summary_key, compute_speedup)
        df = pd.DataFrame(data)

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=[x_key], ascending=False)

        y_key = cfg__summary_key
        if (cfg__speedup or cfg__efficiency) and not has_speedup:
            return None, "Cannot compute the speedup & efficiency (reference value not found)"

        if cfg__speedup:
            y_key += "_speedup"
        elif cfg__efficiency:
            y_key += "_efficiency"


        if has_gpu or has_speedup:
            do_line_plot = True

        elif len(variables) == 1:
            do_line_plot = all(isinstance(v, numbers.Number) for v in list(variables.values())[0])

        else:
            do_line_plot = False


        if do_line_plot:
            color = None if len(variables) == 1 else "name"
            fig = px.line(df, hover_data=df.columns, x=x_key, y=y_key, color=color)

            for i in range(len(fig.data)):
                fig.data[i].update(mode='lines+markers+text')
                fig.update_yaxes(rangemode='tozero')
        else:
            fig = px.bar(df, hover_data=df.columns, x=x_key, y=y_key, color="name")

        if has_gpu:
            fig.update_xaxes(title="Number of GPUs used for the fine-tuning")
        else:
            fig.update_xaxes(title=x_key)

        y_title = getattr(summary_key_properties, "title", "speed")
        y_units = summary_key_properties.units

        if cfg__speedup:
            what = " speedup"
            y_lower_better = False
        elif cfg__efficiency:
            what = " efficiency"
            y_lower_better = False
        else:
            y_lower_better = summary_key_properties.lower_better
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

        if any(map(numpy.isnan, [min_row_idx, max_row_idx])):
            return fig, ["Max or Min is NaN"]

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
            msg.append(("Slowest" if y_lower_better else "Fastest") + f": {df[y_key][max_row_idx]:.2f} {units} ({max_name})")
            msg.append(html.Br())
            msg.append(("Fastest" if y_lower_better else "Slowest") + f": {df[y_key][min_row_idx]:.2f} {units} ({min_name})")

        return fig, msg


def generateSFTTrainerProgressData(entries, x_key, variables, progress_key):
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


class SFTTrainerProgress():
    def __init__(self):
        self.name = "SFTTrainer Progress"
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
