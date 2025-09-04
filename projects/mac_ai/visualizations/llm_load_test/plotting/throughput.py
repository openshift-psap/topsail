from collections import defaultdict
import re
import logging
import datetime
import math
import copy

import statistics as stats

import plotly.subplots
import types

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import error_report, report

def register():
    Throughput()

def _generate_throughput(results):
    if not results.llm_load_test_output: return None

    return results.llm_load_test_output["summary"]["throughput"]


def _generate_time_per_output_token(results):
    if not results.llm_load_test_output: return None

    tpot = dict(results.llm_load_test_output["summary"]["tpot"])
    tpot["values"] = [x["tpot"] for x in results.llm_load_test_output["results"] if x["tpot"]]
    return types.SimpleNamespace(**tpot)


def _generate_inter_token_latency(results):
    if not results.llm_load_test_output: return None

    itl = dict(results.llm_load_test_output["summary"]["itl"])
    itl["values"] = [x["itl"] for x in results.llm_load_test_output["results"] if x["itl"]]
    return types.SimpleNamespace(**itl)


def _generate_time_to_first_token(results):
    if not results.llm_load_test_output: return None

    ttft = dict(results.llm_load_test_output["summary"]["ttft"])
    ttft["values"] = [x["ttft"] for x in results.llm_load_test_output["results"] if x["ttft"]]
    return types.SimpleNamespace(**ttft)


def _generate_failures(results):
    if not results.llm_load_test_output: return None

    return results.llm_load_test_output["summary"]["total_failures"]


def _is_streaming(results):
    return results.test_config.get("test.llm_load_test.args.streaming")


def generateThroughputData(entries, variables, ordered_vars, model_name=None):
    data = []


    for entry in entries:
        llm_data = entry.results.llm_load_test_output
        generatedTokens = 0

        if model_name and entry.settings.__dict__.get("model_name") != model_name:
            continue

        datum = dict(entry.settings.__dict__)

        datum["legend_name"] = entry.settings.__dict__.get(ordered_vars[0]) if ordered_vars else "single-entry"

        datum["test_name"] = entry.get_name([v for v in variables if v != ordered_vars[0]]).replace(", ", "<br>").replace("model_name=", "")
        if len(ordered_vars) == 2:
            datum["test_name"] = datum["test_name"].replace(f"{ordered_vars[1]}=", "")

        datum["test_full_name"] = entry.get_name(variables)

        if datum["test_name"]: datum["test_name"] += "<br>"

        if not entry.results.llm_load_test_output: continue

        datum["throughput"] = _generate_throughput(entry.results)

        datum["tpot_mean"] = _generate_time_per_output_token(entry.results).mean
        datum["itl_mean"] = _generate_inter_token_latency(entry.results).mean
        datum["ttft_mean"] = _generate_time_to_first_token(entry.results).mean

        datum["gen_throughput"] = 1/datum["itl_mean"] * 1000

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
        cfg__ttft = cfg.get("ttft", False)
        cfg__tpot = cfg.get("tpot", False)
        cfg__gen_throughput = cfg.get("gen_throughput", False)

        subtitle = ""
        if cfg__itl:
            y_name = "Inter-Token Latency"
            y_unit = "ms"
            y_key = "itl_mean"
            lower_better = True
        elif cfg__gen_throughput:
            y_name = "Generation Throughput"
            y_unit = "token/s"
            y_key = "gen_throughput"
            lower_better = False
            subtitle = "<br>(1 / Inter-Token Latency)"
        elif cfg__tpot:
            y_name = "Time Per Output Token"
            y_unit = "ms/token"
            y_key = "tpot_mean"
            lower_better = True
        elif cfg__ttft:
            y_name = "Time To First Token"
            y_unit = "ms"
            y_key = "ttft_mean"
            lower_better = True
        else:
            if cfg__bar_plot:
                y_name = "Overall Throughput"
                y_unit = "token/s"
                y_key = "throughput"
                lower_better = False
            else:
                msg = "Throughput/line: must select between between TTFT/ITL/TOPT"
                return None, msg

        entries = [cfg__entry] if cfg__entry else \
            common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateThroughputData(entries, variables, ordered_vars, cfg__model_name))

        if df.empty:
            return None, "Not data available ..."

        if cfg__model_name:
            subtitle += f"<br><b>{cfg__model_name}</b>"

        if cfg__bar_plot:
            df = df.sort_values(by=["test_name"], ascending=True)

            fig = px.bar(df, x='legend_name', y=y_key, color="test_name",
                         hover_data=df.columns, text=y_key, text_auto='.0f')
            title = f"{y_name} (in {y_unit})"
            y_title = f"{y_name} (in {y_unit})"
            if lower_better:
                y_title = f"❮ {y_title}<br>Lower is better"
            else:
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
            fig.update_layout(title=f"{title}{subtitle}", title_x=0.5,)
            fig.update_layout(legend_title_text="Test")

            if ordered_vars:
                fig.update_xaxes(title=ordered_vars[0].title().replace("_", " "))

            if len(ordered_vars) == 2:
                fig.update_layout(legend_title_text=ordered_vars[1].title().replace("_", " "))

            if len(ordered_vars) <= 1:
                fig.layout.update(showlegend=False)
        else:
            df = df.sort_values(by=["legend_name"], ascending=False)

            if len(variables) >= 2:
                color = "legend_name"
                text = "test_name"
            else:
                color = None
                text = "legend_name"

            fig = px.line(df, hover_data=df.columns,
                          x="throughput", y=y_key, color=color, text=text)

            for i in range(len(fig.data)):
                fig.data[i].update(mode='lines+markers+text')

            fig.update_xaxes(title=f"Throughput (in tokens/s) ❯<br>Higher is better")

            fig.update_yaxes(title=f"❮ Mean {y_name} (in {y_unit})<br>Lower is better")
            fig.update_layout(title=f"Throughput vs {y_name}{subtitle}", title_x=0.5,)

            if len(ordered_vars) == 2:
                fig.update_layout(legend_title_text=ordered_vars[1].title())
            else:
                fig.update_layout(legend_title_text="Test")

            if not color or len(df[color].unique()) <= 1:
                fig.layout.update(showlegend=False)

        if cfg__model_name:
            subtitle += f"<br><b>{cfg__model_name}</b>"
        # ❯ or ❮

        return fig, ""
