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

from . import error_report

def register():
    CompletionTimeComparison()
    ExecutionTimeComparison()

class CompletionTimeComparison():
    def __init__(self):
        self.name = "Completion time comparison"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        def time(sec):
            if sec < 0.001:
                return f"0 seconds"
            elif sec < 5:
                return f"{sec:.3f} seconds"
            if sec < 20:
                return f"{sec:.1f} seconds"
            elif sec <= 120:
                return f"{sec:.0f} seconds"
            else:
                return f"{sec/60:.1f} minutes"

        data = []
        text = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            completion_time = error_report._get_time_to_last_completion(entry)
            name = entry.get_name(variables)
            data.append(dict(
                CompletionTime = completion_time,
                Name = name,
            ))
            text.append(f"{name} ran in {time(completion_time)}")
            text.append(html.Br())
        df = pd.DataFrame(data)
        if df.empty:
            return None, "Nothing to plot (no data)"

        fig = px.bar(df, x="Name", y="CompletionTime", color="Name",
                     title=f"Distribution of the completion time")

        fig.update_layout(title_x=0.5,)
        fig.update_layout(xaxis_title="")
        fig.update_layout(yaxis_title="Completion time (in seconds)")

        return fig, text

def ExecutionTimeComparison_generatePodTimes(entry, variables, exclude_workload=["sleep"]):
    data = []

    for p in entry.results.pods_info:
        if p.workload in exclude_workload:
            continue
        workload_phase = dict(
            Duration=(p.container_finished - p.creation_time).total_seconds(),
            Workload=p.workload,
            Experiment=entry.get_name(variables),
        )
        data.append(workload_phase)

    return data


def ExecutionTimeComparison_generateStats(entry, variables, data):
    df = pd.DataFrame(data)
    q1, med, q3 = (0.0, 0.0, 0.0)
    q90 = 0.0
    q100 = 0.0
    if len(df) >= 2:
        q1, med, q3 = stats.quantiles(df.Duration)
        q90 = stats.quantiles(df.Duration, n=10)[8] # 90th percentile
        q100 = df.Duration.max()

    def time(sec):
        if sec < 0.001:
            return f"0 seconds"
        elif sec < 5:
            return f"{sec:.3f} seconds"
        if sec < 20:
            return f"{sec:.1f} seconds"
        elif sec <= 120:
            return f"{sec:.0f} seconds"
        else:
            return f"{sec/60:.1f} minutes"

    msg = []
    msg.append(html.H3(entry.get_name(variables)))

    msg.append(html.Br())
    msg.append(f"25% ran in less than {time(q1)} [Q1]")
    msg.append(html.Br())
    msg.append(f"50% ran in less than {time(med)} (+ {time(med-q1)}) [median]")
    msg.append(html.Br())
    msg.append(f"75% ran in less than {time(q3)} (+ {time(q3-med)}) [Q3]")
    msg.append(html.Br())
    msg.append(f"100% ran in less than {time(q100)} (+ {time(q100-q3)})")

    msg.append(html.Br())

    return [html.Li(msg)]

class ExecutionTimeComparison():
    def __init__(self):
        self.name = "Execution time comparison"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        data = []
        text = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            entry_data = ExecutionTimeComparison_generatePodTimes(entry, variables)
            data += entry_data

            text += ExecutionTimeComparison_generateStats(entry, variables, entry_data)

        df = pd.DataFrame(data)
        if df.empty:
            return None, "Nothing to plot (no data)"

        fig = px.box(df, x="Experiment", y="Duration", color="Workload")

        fig.update_layout(title_x=0.5,)
        fig.update_layout(xaxis_title="")
        fig.update_layout(yaxis_title="Completion time (in seconds)")

        return fig, [html.Ul(text)]
