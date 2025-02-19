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
    Throughput()
    ByUsers()

def generateThroughputData(entries, _variables, _ordered_vars, model_name=None):
    data = []

    variables = dict(_variables) # make a copy before modifying

    has_multiple_modes = True

    variables.pop("index", None)
    variables.pop("model_name", None)
    ordered_vars = [v for v in _ordered_vars if v in variables]

    for entry in entries:
        llm_data = entry.results.llm_load_test_output
        generatedTokens = 0

        if model_name and entry.settings.__dict__.get("model_name") != model_name:
            continue

        datum = dict(entry.settings.__dict__)

        datum["legend_name"] = entry.settings.__dict__.get(ordered_vars[0]) if ordered_vars else "single-entry"

        datum["test_name"] = entry.get_name([v for v in variables if v != ordered_vars[0]]).replace(", ", "<br>").replace("model_name=", "")

        if datum["test_name"]: datum["test_name"] += "<br>"

        if _variables and not has_multiple_modes:
            datum["test_name:sort_index"] = entry.settings.__dict__[list(_variables.keys())[0]]
        else:
            datum["test_name:sort_index"] = datum["test_name"]

        if not entry.results.llm_load_test_output: continue

        datum["throughput"] = entry.results.lts.results.throughput

        datum["vusers"] = entry.results.lts.metadata.settings.virtual_users

        datum["tpot_mean"] = entry.results.lts.kpis["kserve_llm_load_test_tpot_mean"].value
        datum["itl_mean"] = entry.results.lts.kpis["kserve_llm_load_test_itl_mean"].value
        datum["ttft_mean"] = entry.results.lts.kpis["kserve_llm_load_test_ttft_mean"].value

        datum["sort_index"] = entry.settings.__dict__[ordered_vars[0]] \
            if ordered_vars else 0

        data.append(datum)

    return data


class Throughput():
    def __init__(self):
        self.name = "Throughput"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        cfg__entry = cfg.get("entry", None)
        cfg__bar_plot = cfg.get("bar_plot", False)
        cfg__model_name = cfg.get("model_name", False)
        cfg__itl = cfg.get("itl", False)

        entries = [cfg__entry] if cfg__entry else \
            common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateThroughputData(entries, variables, ordered_vars, cfg__model_name))

        if df.empty:
            return None, "Not data available ..."

        vus = ", ".join(map(str, sorted(df["vusers"].unique())))
        subtitle = f"<br>for {vus} users"
        if cfg__model_name:
            subtitle += f"<br><b>{cfg__model_name}</b>"

        if cfg__bar_plot:
            df = df.sort_values(by=["sort_index", "test_name"], ascending=True)

            fig = px.bar(df, x='legend_name', y='throughput', color="test_name", hover_data=df.columns,
                         text='throughput', text_auto='.0f')
            fig.update_layout(barmode='group')
            fig.update_layout(
                yaxis=dict(
                    title="Throughput (in tokens/s) ❯<br>Higher is better",
                    rangemode="tozero",
                ),
            )
            fig.update_xaxes(title=f"")
            fig.layout.update(showlegend=True)
            fig.update_layout(title=f"Throughput{subtitle}", title_x=0.5,)
            fig.update_layout(legend_title_text="Test")

            if cfg__entry or cfg__model_name:
                fig.layout.update(showlegend=False)
        else:
            df = df.sort_values(by=["sort_index", "legend_name"], ascending=False)

            if cfg__itl:
                y_name = "Inter-Token Latency"
                y_unit = "ms"
                y_key = "itl_mean"
            else:
                y_name = "Time Per Output Token"
                y_unit = "ms/token"
                y_key = "tpot_mean"
            color = "legend_name"

            fig = px.line(df, hover_data=df.columns,
                          x="throughput", y=y_key, color=color, text="test_name",)
            for i in range(len(fig.data)):
                fig.data[i].update(mode='lines+markers+text')

            fig.update_xaxes(title=f"Throughput (in tokens/s) ❯<br>Higher is better")

            fig.update_yaxes(title=f"❮ Mean {y_name} (in {y_unit})<br>Lower is better")
            fig.update_layout(title=f"Throughput and {y_name}{subtitle}", title_x=0.5,)
            if ordered_vars:
                fig.update_layout(legend_title_text=ordered_vars[0].title())

            if len(df[color].unique()) <= 1:
                fig.layout.update(showlegend=False)

        if cfg__model_name:
            subtitle += f"<br><b>{cfg__model_name}</b>"
        # ❯ or ❮

        return fig, ""


class ByUsers():
    def __init__(self):
        self.name = "By Users"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        cfg__entry = cfg.get("entry", None)
        cfg__model_name = cfg.get("model_name", False)
        cfg__what = cfg.get("what", False)

        entries = [cfg__entry] if cfg__entry else \
            common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateThroughputData(entries, variables, ordered_vars, cfg__model_name))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["sort_index", "legend_name"], ascending=False)

        if cfg__what == "ttft":
            y_name = "Time To First Token"
            y_unit = "ms"
            y_key = "ttft_mean"
            y_title = f"❮ Mean {y_name} (in {y_unit})<br>Lower is better"
        elif cfg__what == "throughput":
            y_name = "Throughput"
            y_unit = "token/ms"
            y_key = "throughput"
            y_title = f"{y_name} (in {y_unit}) ❯<br>Higher is better"

        fig = px.line(df, hover_data=df.columns,
                      x="vusers", y=y_key, color="legend_name", text="test_name",)
        for i in range(len(fig.data)):
            fig.data[i].update(mode='lines+markers')

        fig.update_xaxes(title=f"Number of Virtual Users")

        fig.update_yaxes(title=y_title)
        subtitle = f"<br><b>{cfg__model_name}</b>" if cfg__model_name else ""
        fig.update_layout(title=f"{y_name} by Virtual Users{subtitle}", title_x=0.5,)
        fig.update_layout(legend_title_text="Model name")

        # ❯ or ❮

        if cfg__entry or cfg__model_name:
            fig.layout.update(showlegend=False)

        return fig, ""
