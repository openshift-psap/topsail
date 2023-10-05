from collections import defaultdict
import re
import logging
import datetime
import math
import copy

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common


def register():
    Latency()
    LatencyDetails()

def generateLatencyData(entries, _variables):
    variables = {v:_variables[v] for v in _variables if v not in ["model_name", "model_id"]}
    data = []
    for entry in entries:
        llm_data = entry.results.llm_load_test_output

        for idx, block in enumerate(llm_data):
            for detail in block["details"]:
                datum = {}
                datum["index"] = idx
                datum["timestamp"] = detail["timestamp"]
                datum["latency"] = detail["latency"] / 1000 / 1000 / 1000
                datum["model_name"] = entry.settings.model_name
                datum["test_name"] = entry.get_name(variables).replace(", ", "<br>")
                data.append(datum)

    return data


class Latency():
    def __init__(self):
        self.name = "Latency"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        df = pd.DataFrame(generateLatencyData(common.Matrix.all_records(settings, setting_lists), variables))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["test_name", "index"])

        fig = px.box(df, hover_data=df.columns,
                      x="model_name", y="latency", color="test_name")


        fig.update_layout(barmode='stack')
        fig.update_yaxes(range=[0, df.latency.max() * 1.1])
        fig.update_layout(title=f"Average latency of the models", title_x=0.5,)
        fig.update_xaxes(title=f"Timeline")
        fig.update_yaxes(title=f"Latency (in seconds)")

        return fig, ""


def generateLatencyDetailsData(entries, _variables):
    variables = {k:v for k,v in _variables.items() if k not in ["model_id"]}

    data = []
    for entry in entries:
        llm_data = entry.results.llm_load_test_output
        for idx, block in enumerate(llm_data):
            for detail in block["details"]:
                datum = {}
                datum["index"] = idx
                datum["timestamp"] = detail["timestamp"]
                datum["latency"] = detail["latency"] / 1000 / 1000 / 1000
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

        entries = [cfg__entry] if cfg__entry else \
            common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateLatencyDetailsData(entries, variables))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["test_name", "timestamp"])

        fig = px.line(df, hover_data=df.columns,
                      x="timestamp", y="latency", color="test_name")


        for i in range(len(fig.data)):
            fig.data[i].update(mode='markers')

        fig.update_layout(barmode='stack')
        fig.update_yaxes(range=[0, df.latency.max() * 1.1])
        fig.update_layout(title=f"Detailed latency of the load test", title_x=0.5,)
        fig.update_xaxes(title=f"Timeline")
        fig.update_yaxes(title=f"Latency (in seconds)")

        return fig, ""
