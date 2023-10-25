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
    LatencyDistribution()
    LatencyDetails()
    ErrorDistribution()
    FinishReasonDistribution()
    LogDistribution()
    SuccessCountDistribution()


class LatencyDistribution():
    def __init__(self):
        self.name = "Latency distribution"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        entries = common.Matrix.all_records(settings, setting_lists)
        cfg__only_tokens = cfg.get("only_tokens", False)
        cfg__summary = cfg.get("summary", False)
        cfg__box_plot = cfg.get("box_plot", True)
        cfg__show_text = cfg.get("show_text", True)

        df = pd.DataFrame(generateLatencyDetailsData(entries, variables, only_tokens=cfg__only_tokens, summary=cfg__summary))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["timestamp"])
        if cfg__only_tokens:
            y_key = "tokens"
        else:
            y_key = "latencyPerToken"

        if cfg__box_plot:
            fig = px.box(df, hover_data=df.columns,
                         x="model_name", y=y_key, color="test_name")
            fig.update_yaxes(range=[0, df[y_key].max() * 1.1])
        else:
            fig = plotCustomComparison(df, x="model_name", y=y_key)

        if cfg__only_tokens:
            plot_title = f"Distribution of the number of tokens of the model answers"
            fig.update_yaxes(title=f"Number of tokens")
        else:
            plot_title = f"Distribution of the latency/token of the model answers"
            fig.update_yaxes(title=f"Latency per token (in ms/token)")

        if "model_name" not in variables:
            plot_title += f"<br><b>{settings['model_name']}</b>"

        fig.update_layout(title=plot_title, title_x=0.5,)
        fig.update_xaxes(title=f"Timeline")

        if len(variables) == 1 and "model_name" in variables:
            fig.layout.update(showlegend=False)

        if cfg__box_plot and cfg__summary:
            fig.layout.update(showlegend=False)

        msg = []
        for test_fullname in df.sort_values(by=["test_fullname"]).test_fullname.unique() if cfg__show_text else []:
            stats_data = df[df.test_fullname == test_fullname][y_key]

            msg += [html.H3(test_fullname)]
            q0 = stats_data.min()
            q100 = stats_data.max()
            q1, med, q3 = stats.quantiles(stats_data)
            q90 = stats.quantiles(stats_data, n=10)[8] # 90th percentile
            if cfg__only_tokens:
                label = "the calls contained less than"
                unit = "tokens"
            else:
                label = "the calls performed faster than"
                unit = "ms/token"

            msg.append(f"0% of {label} {q0:.0f} {unit} [min]")
            msg.append(html.Br())
            msg.append(f"25% of {label} {q1:.0f} {unit} [Q1]")
            msg.append(html.Br())
            msg.append(f"50% of {label} {med:.0f} {unit} (+ {med-q1:.0f} {unit}) [median]")
            msg.append(html.Br())
            msg.append(f"75% of {label} {q3:.0f} {unit} (+ {q3-med:.0f} {unit}) [Q3]")
            msg.append(html.Br())
            msg.append(f"90% of {label} {q90:.0f} {unit} (+ {q90-q3:.0f} {unit}) [90th quantile]")
            msg.append(html.Br())
            msg.append(f"100% of {label} {q100:.0f} {unit} (+ {q100-q90:.0f} {unit}) [max]")
            msg.append(html.Br())
            msg.append(html.Br())
            msg.append(f"There are {len(stats_data)} recorded calls.")
            msg.append(html.Br())
            msg.append(f"The median is {med:.0f} {unit}.")
            msg.append(html.Br())
            q3_q1 = q3 - q1
            msg.append(f"There are {q3_q1:.0f} {unit} between Q1 and Q3 ({q3_q1/med*100:.1f}% of the median).")
            msg.append(html.Br())
            q100_q0 = q100 - q0
            msg.append(f"There are {q100 - q0:.0f} {unit} between min and max ({q100_q0/med*100:.1f}% of the median).")
            msg.append(html.Br())

        return fig, msg


def plotCustomComparison(df, x, y):
    fig = go.Figure()
    data_whatxy = defaultdict(dict)

    for x_value in df[x].unique():
        df_x_value = df[df[x] == x_value]
        y_min = df_x_value[y].min()
        y_max = df_x_value[y].max()
        q1, median, q3 = stats.quantiles(df_x_value[y])

        q90 = stats.quantiles(df_x_value[y], n=10)[8] # 90th percentile
        q99 = stats.quantiles(df_x_value[y], n=100)[98] # 99th percentile

        data_whatxy["max"][x_value] = y_max
        data_whatxy["99th percentile"][x_value] = q99
        data_whatxy["90th percentile"][x_value] = q90
        data_whatxy["Q3 (75%)"][x_value] = q3
        data_whatxy["median (50%)"][x_value] = median
        data_whatxy["Q1 (25%)"][x_value] = q1
        data_whatxy["min"][x_value] = y_min

    all_x_values = set()
    all_y_values = []
    for legend_name, xy_values in data_whatxy.items():
        x_values = list(xy_values.keys())
        y_values = list(xy_values.values())

        all_x_values.update(x_values)
        all_y_values += y_values
        fig.add_trace(go.Bar(x=x_values,
                             y=y_values,
                             name=legend_name,
                             ))
    fig.update_layout(barmode='overlay')

    return fig

def generateLatencyDetailsData(entries, _variables, only_errors=False, test_name_by_error=False, latency_per_token=True, show_errors=False, only_tokens=False, summary=False):
    data = []

    if "mode" in _variables:
        variables = list(_variables) # make a copy before modifying
        variables.remove("mode")
        has_multiple_modes = True
    else:
        variables = _variables
        has_multiple_modes = False

    for entry in entries:
        llm_data = entry.results.llm_load_test_output
        for idx, block in enumerate(llm_data):
            for detail in block["details"]:
                if only_errors and not detail.get("error"):
                    continue # in this plot, ignore the latency if no error occured
                if not show_errors and detail.get("error"):
                    continue

                datum = {}

                datum["timestamp"] = detail["timestamp"]

                generatedTokens = int(detail["response"].get("generatedTokens", 1))
                if only_tokens:
                    datum["tokens"] = generatedTokens

                elif latency_per_token:
                    datum["latencyPerToken"] = detail["latency"] / 1000 / 1000 / generatedTokens # in ms/token

                else:
                    datum["latency"] = detail["latency"] / 1000 / 1000

                datum["model_name"] = f"{entry.settings.model_name}<br>"+entry.get_name([v for v in variables if v not in ("index", "mode", "model_name")]).replace(", ", "<br>")

                if has_multiple_modes:
                    datum["model_name"] += f"<br>{entry.settings.mode.title()}"

                if summary:
                    datum["test_name"] = entry.get_name(v for v in variables if v != "index").replace(", ", "<br>")
                elif test_name_by_error:
                    datum["test_name"] = error_report.simplify_error(detail.get("error"))
                elif detail.get("error"):
                    datum["test_name"] = "errors"
                else:
                    datum["test_name"] = entry.get_name(variables).replace(", ", "<br>")

                if only_errors:
                    datum["error"] = detail.get("error")

                datum["test_fullname"] = datum["model_name"].replace("<br>", ", ")


                data.append(datum)

    return data


def generateErrorHistogramData(entries, variables):
    data = []
    CLOSING_CX = "rpc error: code = Canceled desc = grpc: the client connection is closing"
    CLOSED_CX = "rpc error: code = Unavailable desc = error reading from server: read tcp: use of closed network connection"

    for entry in entries:
        llm_data = entry.results.llm_load_test_output

        errorDistribution = defaultdict(int)
        for idx, block in enumerate(llm_data):
            for descr, count in block.get("errorDistribution", {}).items():
                simplified_error = error_report.simplify_error(descr)

                if error_report.simplify_error(descr) in (CLOSING_CX, CLOSED_CX):
                    continue # ignore these errors from the top chart, they're well known

                errorDistribution[simplified_error] += count


        for descr, count in errorDistribution.items():
            datum = {}
            datum["error"] = descr
            datum["count"] = count
            datum["test_name"] = entry.get_name(variables).replace(", ", "<br>")
            data.append(datum)

    return data


def generateSuccesssCount(entries, variables):
    data = []

    for entry in entries:
        llm_data = entry.results.llm_load_test_output

        success_count = 0
        for idx, block in enumerate(llm_data):
            error_count = 0
            for descr, count in block.get("errorDistribution", {}).items():
                error_count += count
            success_count += len(block["details"]) - error_count
        data.append(dict(
            test_name=entry.get_name(variables),
            count=success_count,
        ))

    return data


def generateFinishReasonData(entries, variables):
    data = []

    for entry in entries:
        llm_data = entry.results.llm_load_test_output

        finishReasons = defaultdict(int)
        for idx, block in enumerate(llm_data):
            for detail in block.get("details"):
                if detail["error"]:
                    reason = "ERROR"
                else:
                    reason = detail["response"].get("finishReason", "ERROR")
                pass
                finishReasons[reason] += 1

        for reason, count in finishReasons.items():
            datum = {}
            datum["reason"] = reason
            datum["count"] = count
            datum["test_name"] = entry.get_name(variables).replace(", ", "<br>")
            data.append(datum)

    return data


class LatencyDetails():
    def __init__(self):
        self.name = "Latency details"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        cfg__entry = cfg.get("entry", None)
        cfg__only_tokens = cfg.get("only_tokens", False)
        cfg__only_errors = cfg.get("only_errors", False)
        cfg__show_errors = cfg.get("show_errors", cfg__only_errors)

        entries = [cfg__entry] if cfg__entry else \
            common.Matrix.all_records(settings, setting_lists)
        latency_per_token = (not cfg__only_errors and not cfg__show_errors)
        df = pd.DataFrame(generateLatencyDetailsData(entries, variables,
                                                     test_name_by_error=cfg__only_errors,
                                                     show_errors=cfg__show_errors,
                                                     only_errors=cfg__only_errors,
                                                     only_tokens=cfg__only_tokens,
                                                     latency_per_token=latency_per_token))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["test_name"])

        if cfg__only_tokens:
            y_key = "tokens"
        elif latency_per_token:
            y_key = "latencyPerToken"
        else:
            y_key = "latency"

        fig = px.line(df, hover_data=df.columns,
                      x="timestamp", y=y_key, color="test_name")


        for i in range(len(fig.data)):
            fig.data[i].update(mode='markers')

        fig.update_layout(barmode='stack')
        fig.update_yaxes(range=[0, df[y_key].max() * 1.1])
        if cfg__entry:
            subtitle = f"<br>{cfg__entry.get_name(reversed(sorted(set(list(variables.keys()) + ['model_name']))))}"
        elif "model_name" not in variables:
            subtitle = f"<br><b>{settings['model_name']}</b>"
        else:
            subtitle = ""

        fig.update_xaxes(title=f"Timeline")
        if cfg__only_tokens:
            fig.update_yaxes(title=f"Number of tokens in the answer")
            fig.update_layout(title=f"Detailed token count of the model answers{subtitle}", title_x=0.5,)
        elif latency_per_token:
            fig.update_yaxes(title=f"Latency per token (in ms/token)")
            fig.update_layout(title=f"Detailed latency/token of {'errors of ' if cfg__only_errors else ''}the load test{subtitle}", title_x=0.5,)
        else:
            fig.update_yaxes(title=f"Latency (in ms)")
            fig.update_layout(title=f"Detailed latency of {'errors of ' if cfg__only_errors else ''}the load test{subtitle}", title_x=0.5,)

        if cfg__only_errors:
            fig.update_layout(legend=dict(yanchor="top",
                                          y=-0.1,
                                          xanchor="left",
                                          x=0.01))

        if cfg__entry:
            fig.layout.update(showlegend=False)

        return fig, ""


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

        fig.update_yaxes(title=f"Error occurence count")

        fig.update_layout(legend=dict(yanchor="top",
                                      y=1.55,
                                      xanchor="left",
                                      x=-0.05))

        return fig, ""

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
            fig.update_yaxes(title=f"Successful calls count")
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

        if cfg__line_count:
            fig.update_layout(title=f"Line predictor logs line count", title_x=0.5,)
            fig.update_yaxes(title=f"Line count")
        else:
            fig.update_layout(title=f"Distribution of well-know messages in the logs", title_x=0.5,)
            fig.update_yaxes(title=f"Occurence count")

        return fig, ""
