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


def generateSFTTrainerSummaryData(entries, x_key, _variables, summary_key, compute_speedup=False, filter_key=None, filter_value=None, y_lower_better=True):
    data = []

    variables = [v for v in _variables if v != x_key]
    if not variables and x_key != "gpu":
        variables += [x_key]

    for entry in entries:
        if filter_key is not None and entry.get_settings()[filter_key] != filter_value:
            continue

        datum = dict()
        if x_key == "gpu":
            datum[x_key] = entry.results.allocated_resources.gpu
        else:
            datum[x_key] = entry.settings.__dict__[x_key]

        datum[summary_key] = getattr(entry.results.sfttrainer_metrics.summary, summary_key, None)

        datum["name"] = entry.get_name(variables).replace("hyper_parameters.", "")
        datum["text"] = "{:.2f}".format(datum[summary_key]) if datum[summary_key] is not None else "None"
        datum["is_computed"] = False

        data.append(datum)

    if not compute_speedup:
        return data, None

    ref = None
    for datum in data:
        if datum[x_key] == 1:
            ref = datum[summary_key]

    if not ref:
        return data, None

    for src_datum in data[:]:

        perfect_datum = src_datum.copy()
        perfect_datum["is_computed"] = True
        perfect_datum["name"] = (perfect_datum["name"] + " perfect scaling").strip()
        perfect_datum[summary_key] = value = ref / src_datum[x_key] \
            if y_lower_better else ref * src_datum[x_key]

        if src_datum[x_key] != 1:
            speedup = ref / src_datum[summary_key]
            efficiency = speedup / src_datum[x_key]
            perfect_datum["text"] = f"{value:.2f}<br>speedup: {speedup:.1f}<br>efficiency: {efficiency:.2f}"

        data.append(perfect_datum)

        if not src_datum["name"]:
            src_datum["name"] = summary_key

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

        cfg__filter_key = cfg.get("filter_key", None)
        cfg__filter_value = cfg.get("filter_value", False)
        cfg__x_key = cfg.get("x_key", None)

        from ..store import parsers
        summary_key_properties = parsers.SFT_TRAINER_SUMMARY_KEYS[cfg__summary_key]
        y_lower_better = summary_key_properties.lower_better

        if not cfg__summary_key:
            raise ValueError("'summary_key' is a mandatory parameter ...")

        entries = common.Matrix.all_records(settings, setting_lists)

        has_gpu = "gpu" in ordered_vars and cfg__filter_key != "gpu"

        x_key =  cfg__x_key
        if x_key is None:
            if has_gpu:
                x_key = "gpu"
            elif "model_name" in ordered_vars:
                x_key = "model_name"
            elif ordered_vars:
                x_key = ordered_vars[0]
            else:
                x_key = "expe"

        compute_speedup = has_gpu

        data, has_speedup = generateSFTTrainerSummaryData(entries, x_key, variables, cfg__summary_key, compute_speedup, cfg__filter_key, cfg__filter_value, y_lower_better)
        df = pd.DataFrame(data)

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=[x_key], ascending=False)

        y_key = cfg__summary_key

        if has_gpu or has_speedup:
            do_line_plot = True

        elif len(variables) == 1:
            do_line_plot = all(isinstance(v, numbers.Number) for v in list(variables.values())[0])
        elif x_key.startswith("hyper_parameters."):
            do_line_plot = True
        else:
            do_line_plot = False

        text = None if len(variables) > 3 else "text"
        if do_line_plot:
            color = None if (len(variables) == 1 and not has_speedup) else "name"
            fig = px.line(df, hover_data=df.columns, x=x_key, y=y_key, color=color, text=text)

            for i in range(len(fig.data)):
                fig.data[i].update(mode='lines+markers+text')
                fig.update_yaxes(rangemode='tozero')

            fig.update_traces(textposition='top center')

        else:
            df = df.sort_values(by=["name", x_key], ascending=True)
            fig = px.bar(df, hover_data=df.columns, x=x_key, y=y_key, color="name", barmode='group', text=text)

        if has_gpu:
            fig.update_xaxes(title="Number of GPUs used for the fine-tuning")
        else:
            fig.update_xaxes(title=x_key)

        y_title = getattr(summary_key_properties, "title", "speed")
        y_units = summary_key_properties.units
        x_name = x_key.replace("hyper_parameters.", "")

        y_lower_better = summary_key_properties.lower_better
        what = f", in {y_units}"

        y_title = f"Fine-tuning {y_title}{what}. "
        title = y_title + "<br>"+("Lower is better" if y_lower_better else "Higher is better")

        if cfg__filter_key == "gpu":
            gpu_count = cfg__filter_value
            title += f". {gpu_count} GPU{'s' if gpu_count > 1 else ''}."

        fig.update_yaxes(title=("❮ " if y_lower_better else "") + y_title + (" ❯" if not y_lower_better else ""))
        fig.update_layout(title=title, title_x=0.5,)
        fig.update_layout(legend_title_text="Configuration")

        fig.update_xaxes(title=x_name)
        # ❯ or ❮

        msg = []

        values_df = df[y_key][df["is_computed"] != True]

        min_row_idx = values_df.idxmin()
        max_row_idx = values_df.idxmax()

        if any(map(numpy.isnan, [min_row_idx, max_row_idx])):
            return fig, ["Max or Min is NaN"]

        min_count = values_df[min_row_idx]
        max_count = values_df[max_row_idx]

        if has_gpu:
            min_name = f"{min_count} GPU" + ("s" if min_count > 1 else "")
            max_name = f"{max_count} GPU" + ("s" if max_count > 1 else "")
        else:
            min_name = min_count
            max_name = max_count

        if len(data) > 1:
            if y_lower_better:
                fastest = df[y_key][min_row_idx]
                slowest = df[y_key][max_row_idx]
            else:
                fastest = df[y_key][max_row_idx]
                slowest = df[y_key][min_row_idx]

            slower = (fastest-slowest)/fastest
            faster = (fastest-slowest)/slowest
            msg.append(f"Fastest: {fastest:.2f} {y_units} ({abs(faster)*100:.0f}% faster, best)")
            msg.append(html.Br())
            msg.append(f"Slowest: {slowest:.2f} {y_units} ({abs(slower)*100:.0f}% slower)")

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
