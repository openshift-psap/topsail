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
    LlamaMicroBenchPlot()
    LlamaMicroBenchComparisonPlot()
    LlamaMicroBenchTable()


def generateLlamaBenchData(entries, variables, ordered_vars, llama_bench_test=None):
    data = []

    for entry in entries:
        datum = dict()

        test_name = entry.get_name([v for v in variables if v != ordered_vars[0]]).replace(", ", "<br>").replace("model_name=", "")
        datum["legend_name"] = entry.settings.__dict__.get(ordered_vars[0]) if ordered_vars else "single-entry"

        for llama_bench_result in (entry.results.llama_bench_results or []):
            if llama_bench_test and llama_bench_result["test"] != llama_bench_test:
                continue

            test_datum = datum.copy() | llama_bench_result

            test_datum["test_name"] = f"{test_datum['test']} | {test_name}" if test_name else test_datum['test']
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

        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateLlamaBenchData(entries, variables, ordered_vars,
                                                 llama_bench_test=cfg__llama_bench_test))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["test_name"], ascending=True)

        fig = px.bar(df, x='legend_name', y=y_key, color="test_name",
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

        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateLlamaBenchData(entries, variables, ordered_vars,
                                                 llama_bench_test=cfg__llama_bench_test))

        if df.empty:
            return None, "Not data available ..."

        df = df.drop(["file_path"], axis=1)

        link_list = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            artifacts_basedir = entry.results.from_local_env.artifacts_basedir

            link_list.append(html.Li(html.A(entry.get_name(variables) or "single-entry", href=artifacts_basedir / entry.results.llama_bench_results[0]["file_path"])))

        links = html.Ul(link_list)

        return None, [df.to_html(), html.H3("Raw files"), links]


def generateLlamaMicroBenchData(entries, _variables, _ordered_vars, group):
    data = []

    variables = dict(_variables) # make a copy before modifying

    has_multiple_modes = True

    variables.pop("index", None)
    variables.pop("model_name", None)
    ordered_vars = [v for v in _ordered_vars if v in variables]

    for entry in entries:
        datum = dict()

        datum["test_name"] = entry.get_name(variables)

        if not entry.results.llama_micro_bench_results:
            return

        for micro_bench_result in entry.results.llama_micro_bench_results.__dict__[group]:
            test_datum = datum.copy() | micro_bench_result.__dict__

            data.append(test_datum)

    return data


def generateLlamaMicroBenchComparisonData(entries, variables, ordered_vars,
                                          ref, comp, group, key):
    first_var = ordered_vars[0] # there's only one var at this point
    ref_entry = None
    cmp_entry = None

    for entry in entries:
        datum = dict()

        datum["test_name"] = entry.get_name(variables)

        if entry.settings.__dict__[first_var] == ref:
            ref_entry = entry
        elif entry.settings.__dict__[first_var] == comp:
            cmp_entry = entry

    if not (ref_entry and cmp_entry):
        logging.warning(f"generateLlamaMicroBenchComparisonData: Couldn't find the reference ({ref}) & comparison ({comp}) entries :/")
        return [], None

    if not (ref_entry.results.llama_micro_bench_results and cmp_entry.results.llama_micro_bench_results):
        logging.warning(f"generateLlamaMicroBenchComparisonData: no micro-benchmark results available ...")
        return [], None


    ref_df = pd.DataFrame([e.__dict__ | {first_var: ref} for e in ref_entry.results.llama_micro_bench_results.__dict__[group]])
    cmp_df = pd.DataFrame([e.__dict__ | {first_var: comp} for e in cmp_entry.results.llama_micro_bench_results.__dict__[group]])

    df = pd.merge(ref_df, cmp_df, on="name", suffixes=("_ref", "_cmp"))

    df["comparison"] = (df[f"{key}_ref"] - df[f"{key}_cmp"]) / df[f"{key}_ref"]
    df[ordered_vars] = comp

    ref_data = []
    for name in df["name"].values:
        ref_data.append(dict(name=name, comparison=0))

    return df, pd.DataFrame(ref_data)


class LlamaMicroBenchPlot():
    def __init__(self):
        self.name = "Llama-micro-bench results plot"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        cfg__llama_micro_bench_group = cfg.get("group", None)

        if cfg__llama_micro_bench_group == "compute":
            y_key = "throughput"
            y_unit = "GFLOPS"
            y_name = y_key
        else:
            y_key = "speed"
            y_unit = "GB/s"
            y_name = y_key

        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateLlamaMicroBenchData(entries, variables, ordered_vars,
                                                      group=cfg__llama_micro_bench_group))

        if df.empty:
            return None, "Not data available ..."

        fig = px.line(df, x='name', y=y_key, color="test_name",
                      hover_data=df.columns)
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

        fig.update_xaxes(visible=False)
        #fig.layout.update(showlegend=False)

        # ❯ or ❮

        return fig, ""


class LlamaMicroBenchComparisonPlot():
    def __init__(self):
        self.name = "Llama-micro-bench comparison plot"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        cfg__llama_micro_bench_group = cfg.get("group", None)
        cfg__llama_micro_bench_ref = cfg.get("ref", None)
        cfg__llama_micro_bench_comp = cfg.get("comp", None)

        if cfg__llama_micro_bench_group == "compute":
            y_key = "throughput"
        else:
            y_key = "speed"

        entries = common.Matrix.all_records(settings, setting_lists)

        df, ref_df = generateLlamaMicroBenchComparisonData(
            entries, variables, ordered_vars,
            ref=cfg__llama_micro_bench_ref,
            comp=cfg__llama_micro_bench_comp,
            group=cfg__llama_micro_bench_group,
            key=y_key,
        )

        if not df or df.empty:
            return None, "Not data available ..."

        fig = px.line(df, x='name', y="comparison", color=ordered_vars[0],
                      hover_data=df.columns)


        fig.add_scatter(x=ref_df['name'], y=ref_df['comparison'], mode='lines', name=f"{cfg__llama_micro_bench_ref} (ref)", line=dict(color="red"))
        fig.data = [fig.data[1], fig.data[0]]

        title = f"Comparison of {ordered_vars[0]} <b>{cfg__llama_micro_bench_ref}</b> (ref) vs <b>{cfg__llama_micro_bench_comp}</b><br><i>{cfg__llama_micro_bench_group.title()}</i> operations. <i>Higher is better.</i>"
        y_title = f"Comparison, in %"
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
        fig.update_layout(legend_title_text=None)
        fig.update_layout(yaxis_tickformat='.0%')
        fig.update_xaxes(visible=False)
        #fig.layout.update(showlegend=False)

        # ❯ or ❮

        return fig, ""


class LlamaMicroBenchTable():
    def __init__(self):
        self.name = "Llama-micro-bench results table"
        self.id_name = self.name
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        cfg__llama_bench_test = cfg.get("llama_bench_test", None)

        link_list = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            artifacts_basedir = entry.results.from_local_env.artifacts_basedir
            if not entry.results.llama_micro_bench_results: continue

            link_list.append(html.Li(html.A(entry.get_name(variables) or "single-entry", href=artifacts_basedir / entry.results.llama_micro_bench_results.file_path)))

        links = html.Ul(link_list)

        return None, [html.H3("Raw files"), links]
