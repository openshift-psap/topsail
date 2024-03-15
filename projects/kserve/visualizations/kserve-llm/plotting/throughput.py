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
    TtftConcurrency()

def generateThroughputData(entries, _variables, _ordered_vars, model_name=None):
    data = []

    if "mode" in _variables:
        variables = dict(_variables) # make a copy before modifying
        variables.pop("mode")
        has_multiple_modes = True
    else:
        variables = dict(_variables)
        has_multiple_modes = False

    variables.pop("index", None)
    variables.pop("model_name", None)
    ordered_vars = [v for v in _ordered_vars if v in variables]

    for entry in entries:
        llm_data = entry.results.llm_load_test_output
        generatedTokens = 0

        if model_name and entry.settings.__dict__.get("model_name") != model_name:
            continue

        datum = dict(entry.settings.__dict__)

        datum["model_testname"] = f"{entry.settings.model_name}<br>#{entry.settings.__dict__.get('index', '')}"
        datum["test_name"] = entry.get_name(variables).replace(", ", "<br>").replace("model_name=", "")

        if has_multiple_modes:
            if datum["test_name"]: datum["test_name"] += "<br>"
            datum["test_name"] += f"{entry.settings.mode.title()}"

        if _variables and not has_multiple_modes:
            datum["test_name:sort_index"] = entry.settings.__dict__[list(_variables.keys())[0]]
        else:
            datum["test_name:sort_index"] = datum["test_name"]

        if not entry.results.llm_load_test_output: continue

        duration = (entry.results.test_start_end.end-entry.results.test_start_end.start).total_seconds()
        datum["duration"] = int(duration)

        datum["throughput"] = entry.results.lts.results.throughput
        try:
            datum["vusers"] = entry.settings.concurrency
        except AttributeError:
            datum["vusers"] = entry.results.test_config.get("tests.e2e.llm_load_test.args.concurrency")

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

        if cfg__bar_plot:
            df = df.sort_values(by=["sort_index", "test_name"], ascending=True)

            fig = px.bar(df, x='model_testname', y='throughput', color="test_name", hover_data=df.columns,
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
        else:
            df = df.sort_values(by=["sort_index", "model_testname"], ascending=False)

            if cfg__itl:
                y_name = "Inter-Token Latency"
                y_unit = "ms"
                y_key = "itl_mean"
            else:
                y_name = "Time Per Output Token"
                y_unit = "ms/token"
                y_key = "tpot_mean"

            fig = px.line(df, hover_data=df.columns,
                          x="throughput", y=y_key, color="model_testname", text="test_name",)
            for i in range(len(fig.data)):
                fig.data[i].update(mode='lines+markers+text')

            fig.update_xaxes(title=f"Throughput (in tokens/s) ❯<br>Higher is better")

            fig.update_yaxes(title=f"❮ Mean {y_name} (in {y_unit})<br>Lower is better")
            fig.update_layout(title=f"Throughput and {y_name}{subtitle}", title_x=0.5,)
            fig.update_layout(legend_title_text="Model name")

        if cfg__model_name:
            subtitle += f" ({cfg__model_name})"
        # ❯ or ❮

        if cfg__entry:
            fig.layout.update(showlegend=False)

        return fig, ""


class TtftConcurrency():
    def __init__(self):
        self.name = "TTFT Concurrency"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        cfg__entry = cfg.get("entry", None)
        cfg__model_name = cfg.get("model_name", False)

        entries = [cfg__entry] if cfg__entry else \
            common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateThroughputData(entries, variables, ordered_vars, cfg__model_name))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["sort_index", "model_testname"], ascending=False)

        y_name = "Time To First Token"
        y_unit = "ms"
        y_key = "ttft_mean"

        fig = px.line(df, hover_data=df.columns,
                      x="vusers", y=y_key, color="model_testname", text="test_name",)
        for i in range(len(fig.data)):
            fig.data[i].update(mode='lines+markers')

        fig.update_xaxes(title=f"Number of Virtual Users")

        fig.update_yaxes(title=f"❮ Mean {y_name} (in {y_unit})<br>Lower is better")
        subtitle = f" ({cfg__model_name})" if cfg__model_name else ""
        fig.update_layout(title=f"{y_name} vs Virtual Users{subtitle}", title_x=0.5,)
        fig.update_layout(legend_title_text="Model name")

        # ❯ or ❮

        if cfg__entry:
            fig.layout.update(showlegend=False)

        return fig, ""
