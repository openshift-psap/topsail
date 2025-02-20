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
    GPUUsage(by_freq=True)
    GPUUsage(by_power=True)
    GPUUsage(by_idle=True)


def generateGPUUsageData(entries, _variables, _ordered_vars, key):
    data = []

    variables = dict(_variables) # make a copy before modifying

    ordered_vars = [v for v in _ordered_vars if v in variables]

    for entry in entries:
        if not entry.results.gpu_power_usage: continue

        entry_name = entry.get_name(variables)
        for gpu_power_usage in entry.results.gpu_power_usage.usage:
            entry_data = dict()
            entry_data["name"] = entry_name
            entry_data["ts"] = gpu_power_usage.ts
            entry_data[key] = gpu_power_usage.__dict__[key]

            data.append(entry_data)

    return data


class GPUUsage():
    def __init__(self, by_freq=False, by_power=False, by_idle=False):
        self.name = "GPU Usage"
        if by_freq:
            self.name += " by frequency"
            self.key = "frequency_mhz"
        elif by_power:
            self.name += " by power"
            self.key = "power_mw"
        elif by_idle:
            self.name += " by idle"
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

        df = pd.DataFrame(generateGPUUsageData(entries, variables, ordered_vars, self.key))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["ts", "name"], ascending=False)
        fig = px.line(df, hover_data=df.columns,
                      x="ts", y=self.key, color="name")

        fig.update_yaxes(title=f"{self.key}")

        fig.update_layout(title=self.name, title_x=0.5,)

        return fig, ""
