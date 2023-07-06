from collections import defaultdict
import datetime
import statistics as stats
import logging

from dash import html
import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    PodProgress()

def generate_data(entry):
    data = []

    aw_count = entry.results.test_case_config["aw"]["count"]

    start_time = entry.results.test_start_end_time.start

    def delta(ts):
        return (ts - start_time).total_seconds() / 60

    data.append(dict(
        Delta = delta(start_time),
        Count = 0,
        Percentage = 0,
        Timestamp = start_time,
    ))

    count = 0
    YOTA = datetime.timedelta(microseconds=1)
    for pod_time in sorted(entry.results.pod_times, key=lambda t: t.container_finished):
        if not getattr(pod_time, "container_finished", False):
            continue # not finished, ignore

        data.append(dict(
            Delta = delta(pod_time.container_finished),
            Count = count,
            Percentage = count / aw_count,
            Timestamp = pod_time.container_finished,
        ))
        count += 1
        data.append(dict(
            Delta = delta(pod_time.container_finished),
            Count = count,
            Percentage = count / aw_count,
            Timestamp = pod_time.container_finished,
        ))

    data.append(dict(
        Delta = delta(entry.results.test_start_end_time.end),
        Count = count,
        Percentage = count / aw_count,
        Timestamp = entry.results.test_start_end_time.end,
    ))

    return data

class PodProgress():
    def __init__(self):
        self.name = "Pod Completion Progress"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        expe_cnt = common.Matrix.count_records(settings, setting_lists)
        if expe_cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {expe_cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            pass # entry is set

        data = generate_data(entry)

        df = pd.DataFrame(data)

        cfg__percentage = cfg.get("show_percentage", True)

        fig = px.area(df, x="Delta", y="Percentage" if cfg__percentage else "Count", hover_data=df.columns)

        aw_count = entry.results.test_case_config["aw"]["count"]
        fig.update_xaxes(title="Timeline, in minutes after the start time")
        fig.update_layout(title=f"Pod Completion Progress<br>for a total of {aw_count} Pods", title_x=0.5)

        if cfg__percentage:
            fig.layout.yaxis.tickformat = ',.0%'

        return fig, ""
