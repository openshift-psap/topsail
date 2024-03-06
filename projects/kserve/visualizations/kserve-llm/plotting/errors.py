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

from . import error_report, report

def register():
    ErrorDistribution()
    FinishReasonDistribution()
    LogDistribution()
    SuccessCountDistribution()
    LoadTime()


def generateErrorHistogramData(entries, variables):
    data = []
    CLOSING_CX = "rpc error: code = Canceled desc = grpc: the client connection is closing"
    CLOSED_CX = "rpc error: code = Unavailable desc = error reading from server: read tcp: use of closed network connection"

    for entry in entries:
        if not entry.results.llm_load_test_output: continue

        errorDistribution = defaultdict(int)
        for result in entry.results.llm_load_test_output["results"]:
            simplified_error = error_report.simplify_error(result["error_text"])
            if not simplified_error:
                continue

            if error_report.simplify_error(descr) in (CLOSING_CX, CLOSED_CX, None):
                continue # ignore these errors from the top chart, they're well known

            errorDistribution[simplified_error] += count


        for descr, count in errorDistribution.items():
            datum = {}
            datum["error"] = descr
            datum["count"] = count
            datum["test_name"] = entry.get_name(variables).replace(", ", "<br>")
            data.append(datum)

    return data


class ErrorDistribution():
    def __init__(self):
        self.name = "Errors distribution"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateErrorHistogramData(entries, variables))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["test_name"])

        fig = px.bar(df, hover_data=df.columns,
                     x="test_name", y="count", color="error")


        fig.update_layout(title=f"Distribution of the load test errors", title_x=0.5,)

        fig.update_yaxes(title=f"❮ Error occurence count")

        fig.update_layout(legend=dict(yanchor="top",
                                      y=1.55,
                                      xanchor="left",
                                      x=-0.05))

        return fig, ""

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

def generateFinishReasonData(entries, variables):
    data = []

    for entry in entries:
        if not entry.results.llm_load_test_output: continue

        finishReasons = defaultdict(int)
        for result in entry.results.llm_load_test_output["results"]:
            if result["error_code"] is not None:
                reason = "ERROR"
            else:
                reason = result.get("stop_reason")
                if reason is None: continue

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
            datum["count"] = predictor_logs.line_count
            data.append(datum)
        else:
            for key, count in predictor_logs.distribution.items():
                d = dict(datum)
                d["what"] = key
                d["count"] = count
                data.append(d)

    return data


class LogDistribution():
    def __init__(self):
        self.name = "Log distribution"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        entries = common.Matrix.all_records(settings, setting_lists)
        cfg__line_count = cfg.get("line_count", True)
        df = pd.DataFrame(generateLogData(entries, variables, cfg__line_count))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["test_name"])

        fig = px.bar(df, hover_data=df.columns,
                     x="test_name", y="count", color="test_name" if cfg__line_count else "what")

        subtitle = ""
        if "model_name" not in variables:
            subtitle = f"<br><b>{settings['model_name']}</b>"
        if cfg__line_count:
            fig.update_layout(title=f"Logs line count of the predictor Pod" + subtitle, title_x=0.5,)
            fig.update_yaxes(title=f"❮ Line count")
        else:
            fig.update_layout(title=f"Distribution of well-know messages in the logs" + subtitle, title_x=0.5,)
            fig.update_yaxes(title=f"Occurence count")

        return fig, ""

# ---

def generateLoadTimeData(entries, variables):
    data = []

    for entry in entries:
        predictor_logs = entry.results.predictor_logs

        datum = {}
        datum["test_name"] = entry.get_name(variables).replace(", ", "<br>")
        datum["init_time"] = entry.results.predictor_pod.init_time.total_seconds()
        datum["load_time"] = entry.results.predictor_pod.load_time.total_seconds()
        data.append(datum)

    return data


class LoadTime():
    def __init__(self):
        self.name = "Load time"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        entries = common.Matrix.all_records(settings, setting_lists)
        cfg__init_time = cfg.get("init_time", False)

        df = pd.DataFrame(generateLoadTimeData(entries, variables))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["test_name"])

        if cfg__init_time:
            y_key = "init_time"
            what = "init"
        else:
            y_key = "load_time"
            what = "load"

        fig = px.bar(df, hover_data=df.columns, x="test_name", y=y_key, color="test_name")

        subtitle = ""
        if "model_name" not in variables:
            subtitle = f"<br><b>{settings['model_name']}</b>"


        fig.update_layout(title=f"{what.title()} time of the predictor Pod" + subtitle, title_x=0.5,)
        fig.update_yaxes(title=f"Load time, in seconds")


        return fig, ""
