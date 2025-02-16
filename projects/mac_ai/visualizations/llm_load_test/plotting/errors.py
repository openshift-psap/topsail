from collections import defaultdict
import re
import logging
import datetime
import math
import copy

import statistics as stats

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common
import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report

from . import error_report

def register():
    FinishReasonDistribution()
    SuccessCountDistribution()


# ---

def generateSuccesssCount(entries, variables):
    data = []

    for entry in entries:
        if entry.results.llm_load_test_output:
            llm_data = entry.results.llm_load_test_output

            error_count = llm_data["summary"]["total_failures"]
            success_count = llm_data["summary"]["total_requests"] - error_count
        else:
            error_count = 0
            success_count = 0

        data.append(dict(
            test_name=entry.get_name(variables),
            count=success_count,
        ))

    return data


class SuccessCountDistribution():
    def __init__(self):
        self.name = "Success count distribution"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, *args):
        stats = table_stats.TableStats.stats_by_name["Finish Reason distribution"]
        return stats.do_plot(*report.set_config(dict(success_count=True), args))

# ---

# See https://github.com/IBM/vllm/blob/21fb852e754158a37230cfa6e7faf77c0b814896/vllm/entrypoints/grpc/grpc_server.py#L415
def convertvLLMFinishReason(reason):
    if reason == "length":
        return 1 #TODO could also be 6 / TOKEN_LIMIT
    elif reason == "stop":
        return 2 #TODO could also be 5 / STOP_SEQUENCE
    elif reason == "abort":
        return 3
    else:
        logging.warning("Unrecognized finish_reason: %s", reason)
        return None


def generateFinishReasonData(entries, variables):
    # https://github.com/IBM/text-generation-inference/blob/88f2a0b858b9f080f42cde388c4ebec961b9fa7d/proto/generation.proto#L155-L172
    STOP_REASONS = {
        # Possibly more tokens to be streamed
        0: "NOT_FINISHED",
        # Maximum requested tokens reached
        1: "MAX_TOKENS",
        # End-of-sequence token encountered
        2: "EOS_TOKEN",
        # Request cancelled by client
        3: "CANCELLED",
        # Time limit reached
        4: "TIME_LIMIT",
        # Stop sequence encountered
        5: "STOP_SEQUENCE",
        # Total token limit reached
        6: "TOKEN_LIMIT",
        # Decoding error
        7: "ERROR",
        # Stop reason is not reported
        None: "NOT_REPORTED"
    }

    data = []

    for entry in entries:
        if not entry.results.llm_load_test_output: continue

        finishReasons = defaultdict(int)
        for result in entry.results.llm_load_test_output["results"]:
            reason = result.get("stop_reason")
            if result["error_code"] is not None:
                reason = error_report.simplify_error(result["error_text"])

            #elif reason == 1: # MAX_TOKENS: good, ignore
            #    continue
            else:
                if isinstance(reason, str): # vLLM
                    reason = STOP_REASONS[convertvLLMFinishReason(reason)]
                else:
                    reason = STOP_REASONS[reason]

            finishReasons[reason] += 1

        for reason, count in finishReasons.items():
            datum = {}
            datum["reason"] = reason
            datum["count"] = count
            datum["test_name"] = entry.get_name(variables).replace(", ", "<br>")
            data.append(datum)

    return data


class FinishReasonDistribution():
    def __init__(self):
        self.name = "Finish Reason distribution"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        cfg__success_count = cfg.get("success_count", None)

        entries = common.Matrix.all_records(settings, setting_lists)

        generateData = generateSuccesssCount \
            if cfg__success_count \
               else generateFinishReasonData

        df = pd.DataFrame(generateData(entries, variables))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["test_name"])

        fig = px.bar(df, hover_data=df.columns,
                     x="test_name", y="count", color="test_name" if cfg__success_count else "reason")

        if cfg__success_count:
            fig.update_layout(title=f"Distribution of the successful calls count", title_x=0.5,)
            fig.update_yaxes(title=f"Successful calls count ❯")
            fig.update_xaxes(title=f"")
            fig.layout.update(showlegend=False)
        else:
            fig.update_layout(title=f"Distribution of the finish reasons", title_x=0.5,)
            fig.update_yaxes(title=f"Finish reason count")

        fig.update_layout(legend=dict(yanchor="top",
                                      y=1.55,
                                      xanchor="left",
                                      x=-0.05))

        return fig, ""


# ---

def generateLogData(entries, variables, line_count):
    data = []

    for entry in entries:
        predictor_logs = entry.results.predictor_logs

        datum = {}
        datum["test_name"] = entry.get_name(variables).replace(", ", "<br>")
        if line_count:
            datum["count"] = 0
            data.append(datum)
        else:
            for key, count in predictor_logs.distribution.items():
                d = dict(datum)
                d["what"] = key
                d["count"] = count
                data.append(d)

    return data

# ---

def generateLoadTimeData(entries, variables):
    data = []

    for entry in entries:
        predictor_logs = entry.results.predictor_logs

        datum = {}
        datum["test_name"] = entry.get_name(variables).replace(", ", "<br>")
        data.append(datum)

    return data
