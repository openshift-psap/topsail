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

def generate_pod_progress_data(entry, key):
    data = []

    total_pod_count = entry.results.test_case_properties.total_pod_count

    start_time = entry.results.test_start_end_time.start

    def delta(ts):
        return (ts - start_time).total_seconds() / 60

    name = key.replace("_", " ").title()

    data.append(dict(
        Delta = delta(start_time),
        Count = 0,
        Percentage = 0,
        Timestamp = start_time,
        Name = name,
    ))

    count = 0
    YOTA = datetime.timedelta(microseconds=1)
    for pod_time in sorted(entry.results.pod_times, key=lambda t: getattr(t, key, 0)):
        if not getattr(pod_time, key, False):
            continue

        ts = getattr(pod_time, key)
        time_delta = delta(ts)
        data.append(dict(
            Delta = time_delta,
            Count = count,
            Percentage = count / total_pod_count,
            Timestamp = ts,
            Name = name,
        ))
        count += 1
        data.append(dict(
            Delta = time_delta,
            Count = count,
            Percentage = count / total_pod_count,
            Timestamp = ts,
            Name = name,
        ))

    data.append(dict(
        Delta = delta(entry.results.test_start_end_time.end),
        Count = count,
        Percentage = count / total_pod_count,
        Timestamp = entry.results.test_start_end_time.end,
        Name = name,
    ))

    return data


def generate_launch_progress_data(entry):
    data = []

    total_resource_count = entry.results.test_case_properties.aw_count

    start_time = entry.results.test_start_end_time.start

    def delta(ts):
        return (ts - start_time).total_seconds() / 60

    target_kind = "Job" if entry.results.test_case_properties.job_mode else "AppWrapper"
    name = f"{target_kind}s launched"

    data.append(dict(
        Delta = delta(start_time),
        Count = 0,
        Percentage = 0,
        Timestamp = start_time,
        Name = name,
    ))

    count = 0
    YOTA = datetime.timedelta(microseconds=1)

    for resource_time in entry.results.resource_times.values():
        if resource_time.kind != target_kind: continue

        count += 1
        data.append(dict(
            Delta = delta(resource_time.creation),
            Count = count,
            Percentage = count / total_resource_count,
            Timestamp = resource_time.creation,
            Name = name,
        ))


    data.append(dict(
        Delta = delta(entry.results.test_start_end_time.end),
        Count = count,
        Percentage = count / total_resource_count,
        Timestamp = entry.results.test_start_end_time.end,
        Name = name,
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

        data = []
        data += generate_launch_progress_data(entry)
        for key in "pod_scheduled", "container_finished":
            data += generate_pod_progress_data(entry, key)

        df = pd.DataFrame(data)

        fig = go.Figure()
        for name in df.Name.unique():
            df_name = df[df.Name == name]
            fig.add_trace(go.Scatter(x=df_name.Timestamp,
                                     y=df_name.Percentage,
                                     fill="tozeroy",
                                     mode='lines',
                                     name=name,
                                 ))

        total_pod_count = entry.results.test_case_properties.total_pod_count
        fig.update_yaxes(title="Percentage")
        fig.update_xaxes(title="Timeline, in minutes after the start time")
        schedule_object_kind = "Job" if entry.results.test_case_properties.job_mode else "AppWrapper"
        fig.update_layout(title=f"Pod Completion Progress<br>for a total of {total_pod_count} {schedule_object_kind}s", title_x=0.5)

        fig.layout.yaxis.tickformat = ',.0%'

        return fig, ""
