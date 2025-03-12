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
    LlamaBenchPlot()
    LlamaBenchTable()


def generateLlamaBenchData(entries, _variables, _ordered_vars, llama_bench_test=None):
    data = []

    variables = dict(_variables) # make a copy before modifying

    has_multiple_modes = True

    variables.pop("index", None)
    variables.pop("model_name", None)
    ordered_vars = [v for v in _ordered_vars if v in variables]

    for entry in entries:
        datum = dict()

        datum["test_name"] = entry.get_name([v for v in variables if v != ordered_vars[0]]).replace(", ", "<br>").replace("model_name=", "")
        datum["legend_name"] = entry.settings.__dict__.get(ordered_vars[0]) if ordered_vars else "single-entry"

        if _variables and not has_multiple_modes:
            datum["test_name:sort_index"] = entry.settings.__dict__[list(_variables.keys())[0]]
        else:
            datum["test_name:sort_index"] = datum["test_name"]


        for llama_bench_result in entry.results.llama_bench_results:
            if llama_bench_test and llama_bench_result["test"] != llama_bench_test:
                continue

            test_datum = datum.copy() | llama_bench_result

            data.append(test_datum)

    return data


class LlamaBenchPlot():
    def __init__(self):
        self.name = "Llama-bench results plot"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        cfg__llama_bench_test = cfg.get("llama_bench_test", None)

        y_name = "Throughput"
        y_unit = "tokens/s"
        y_key = "t/s"
        lower_better = False

        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateLlamaBenchData(entries, variables, ordered_vars,
                                                 llama_bench_test=cfg__llama_bench_test))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["test_name:sort_index", "test_name"], ascending=True)

        fig = px.bar(df, x='legend_name', y=y_key, color="test",
                     hover_data=df.columns, text=y_key, text_auto='.0f')
        title = f"{y_name} (in {y_unit})"
        y_title = f"{y_name} (in {y_unit})"

        y_title += " ❯<br>Higher is better"

        fig.update_layout(barmode='group')
        fig.update_layout(
            yaxis=dict(
                title=y_title,
                rangemode="tozero",
            ),
        )
        fig.update_xaxes(title=f"")
        fig.layout.update(showlegend=True)
        fig.update_layout(title=f"{title}", title_x=0.5,)
        fig.update_layout(legend_title_text="Test")

        #fig.layout.update(showlegend=False)

        # ❯ or ❮

        return fig, ""


class LlamaBenchTable():
    def __init__(self):
        self.name = "Llama-bench results table"
        self.id_name = self.name
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        cfg__llama_bench_test = cfg.get("llama_bench_test", None)

        y_name = "Throughput"
        y_unit = "tokens/s"
        y_key = "t/s"
        lower_better = True

        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateLlamaBenchData(entries, variables, ordered_vars,
                                                 llama_bench_test=cfg__llama_bench_test))

        if df.empty:
            return None, "Not data available ..."

        df = df.drop(["test_name:sort_index", "file_path"], axis=1)

        link_list = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            artifacts_basedir = entry.results.from_local_env.artifacts_basedir

            link_list.append(html.Li(html.A(entry.get_name(variables) or "single-entry", href=artifacts_basedir / entry.results.llama_bench_results[0]["file_path"])))

        links = html.Ul(link_list)

        return None, [df.to_html(), html.H3("Raw files"), links]
