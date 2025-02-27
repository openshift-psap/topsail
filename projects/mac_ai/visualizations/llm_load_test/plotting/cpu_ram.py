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
    CPU(by_idle=True)
    RAM(by_unused=True)


def generateCpuRamUsageData(entries, _variables, _ordered_vars,
                            primary_key, secondary_key):
    data = []

    variables = dict(_variables) # make a copy before modifying

    ordered_vars = [v for v in _ordered_vars if v in variables]

    for entry in entries:
        if not entry.results.cpu_ram_usage: continue

        entry_name = entry.get_name(variables)
        for idx, hw_usage in enumerate(entry.results.cpu_ram_usage.__dict__[primary_key]):
            entry_data = dict()
            entry_data["name"] = entry_name
            entry_data["ts"] = idx
            entry_data[secondary_key] = hw_usage.__dict__[secondary_key]

            data.append(entry_data)

    return data


class CPU():
    def __init__(self, by_idle=False):
        self.name = "CPU Usage"
        if by_idle:
            self.name += " by idle time"
            self.key = "idle_pct"
        else:
            raise ValueError("No flavor selected ...")

        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateCpuRamUsageData(entries, variables, ordered_vars, "cpu", self.key))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["ts", "name"], ascending=False)
        fig = px.line(df, hover_data=df.columns,
                      x="ts", y=self.key, color="name")

        fig.update_yaxes(title=f"{self.key}")

        fig.update_layout(title=self.name, title_x=0.5,)

        return fig, ""


class RAM():
    def __init__(self, by_unused=False):
        self.name = "RAM Usage"
        if by_unused:
            self.name += " by unused"
            self.key = "unused_mb"
        else:
            raise ValueError("No flavor selected ...")

        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateCpuRamUsageData(entries, variables, ordered_vars, "memory", self.key))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["ts", "name"], ascending=False)
        fig = px.line(df, hover_data=df.columns,
                      x="ts", y=self.key, color="name")

        fig.update_yaxes(title=f"{self.key}")

        fig.update_layout(title=self.name, title_x=0.5,)

        return fig, ""
