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

def generateThroughputData(entries, _variables):
    data = []

    if "mode" in _variables:
        variables = dict(_variables) # make a copy before modifying
        variables.pop("mode")
        variables.pop("index")
        has_multiple_modes = True
    else:
        variables = dict(_variables)
        has_multiple_modes = False

    for entry in entries:
        llm_data = entry.results.llm_load_test_output
        generatedTokens = 0

        datum = {}
        datum["model_name"] = (f"{entry.settings.model_name}<br>"+entry.get_name([v for v in variables if v not in ("index", "mode", "model_name")]).replace(", ", "<br>")).removesuffix("<br>")
        datum["test_name"] = entry.get_name(variables).replace(", ", "<br>").replace("model_name=", "")
        if has_multiple_modes:
            datum["model_name"] += f"<br>{entry.settings.mode.title()}"
            datum["test_name"] += f"<br>{entry.settings.mode.title()}"

        if _variables and not has_multiple_modes:
            datum["test_name:sort_index"] = entry.settings.__dict__[list(_variables.keys())[0]]
        else:
            datum["test_name:sort_index"] = datum["test_name"]

        calls_count = 0
        latency_s = 0.0
        for idx, block in enumerate(llm_data):
            for detail in block["details"]:
                generatedTokens += int(detail["response"].get("generatedTokens", 1))
                calls_count += 1
                latency_s += detail["latency"] / 1000 / 1000 / 1000

        duration = (entry.results.test_start_end.end-entry.results.test_start_end.start).total_seconds()
        datum["duration"] = int(duration)

        datum["token_count"] = generatedTokens
        datum["throughput"] = int(generatedTokens / duration)
        try:
            datum["vusers"] = entry.settings.threads
        except AttributeError:
            datum["vusers"] = entry.results.test_config.get("tests.e2e.llm_load_test.threads")

        datum["avg_latency"] = latency_s / calls_count

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
        cfg__by_model = cfg.get("by_model", False)

        entries = [cfg__entry] if cfg__entry else \
            common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateThroughputData(entries, variables))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["test_name:sort_index"], ascending=False)

        if cfg__by_model:
            fig = plotly.subplots.make_subplots(rows=1, cols=2, specs=[[{}, {}]], shared_xaxes=True,
                                                shared_yaxes=False, vertical_spacing=0.001)

            fig1 = px.bar(df, hover_data=df.columns, y="test_name", x="throughput", orientation='h')

            for i in range(len(fig1.data)):
                fig1.data[i].update(xperiodalignment="middle")

            fig2 = px.line(df, hover_data=df.columns, y="test_name", x="avg_latency")
            fig2.update_traces(yaxis="y2")
            for i in range(len(fig2.data)):
                fig2.data[i].update(mode='markers+lines')

            fig.add_traces(fig1.data, 1, 1)
            fig.add_traces(fig2.data[0], 1, 2)

            fig.update_layout(
                xaxis=dict(
                    zeroline=False,
                    showline=False,
                    showticklabels=True,
                    showgrid=True,
                    domain=[0, 0.42],
                    title="Throughput (in tokens/s) ❯<br>Higher is better",
                    side='top',
                ),
                yaxis=dict(
                    showgrid=False,
                    showline=False,
                    showticklabels=True,
                    domain=[0, 0.85],
                ),

                xaxis2=dict(
                    zeroline=True,
                    showline=False,
                    showticklabels=True,
                    showgrid=True,
                    domain=[0.47, 1],
                    title="❮ Average latency (in s)<br>Lower is better",
                    side='top',
                ),
                yaxis2=dict(
                    showgrid=False,
                    showline=True,
                    showticklabels=False,
                    linecolor='rgba(102, 102, 102, 0.8)',
                    linewidth=2,
                    domain=[0, 0.85],
                ),
            )
        else:
            fig = px.line(df, hover_data=df.columns, x="throughput", y="avg_latency", color="test_name", text="test_name")
            for i in range(len(fig.data)):
                fig.data[i].update(mode='markers+text')

            fig.update_xaxes(title=f"Throughput (in tokens/s) ❯<br>Higher is better")
            fig.update_yaxes(title=f"❮ Average latency (in s)<br>Lower is better")

        vus = ", ".join(map(str, sorted(df["vusers"].unique())))
        subtitle = f"<br>for {vus} VUs"

        # ❯ or ❮
        fig.update_layout(title=f"Throughput and latency of the load tests{subtitle}", title_x=0.5,)
        if cfg__entry:
            fig.layout.update(showlegend=False)

        return fig, ""
