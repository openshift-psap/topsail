from collections import defaultdict
import datetime
import statistics as stats
import logging
import datetime

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
    if name == "Creation Time":
        name = "Pod Creation"

    data.append(dict(
        Delta = delta(start_time),
        Count = 0,
        Percentage = 0,
        Timestamp = start_time,
        Name = name,
        ResourceName = "started",
    ))

    count = 0
    YOTA = datetime.timedelta(microseconds=1)
    for pod_time in sorted(entry.results.pod_times, key=lambda t: getattr(t, key, datetime.datetime.now())):
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
            ResourceName = pod_time.pod_name,
        ))
        count += 1
        data.append(dict(
            Delta = time_delta,
            Count = count,
            Percentage = count / total_pod_count,
            Timestamp = ts,
            Name = name,
            ResourceName = pod_time.pod_name,
        ))

    return data


def generate_launch_progress_data(entry, resource_kind=None):
    data = []

    total_resource_count = entry.results.test_case_properties.count

    start_time = entry.results.test_start_end_time.start

    def delta(ts):
        return (ts - start_time).total_seconds() / 60

    if resource_kind is None:
        resource_kind = entry.results.target_kind
        resource_kind_name = entry.results.target_kind_name
    else:
        resource_kind_name = resource_kind

    name = f"{resource_kind_name} Created"

    data.append(dict(
        Delta = delta(start_time),
        Count = 0,
        Percentage = 0,
        Timestamp = start_time,
        Name = name,
        ResourceName = "started",
    ))

    count = 0
    YOTA = datetime.timedelta(microseconds=1)

    for resource_time in sorted(entry.results.resource_times.values(), key=lambda t: t.creation):
        if resource_time.kind != resource_kind: continue

        count += 1
        data.append(dict(
            Delta = delta(resource_time.creation),
            Count = count,
            Percentage = count / total_resource_count,
            Timestamp = resource_time.creation,
            Name = name,
            ResourceName = resource_time.name,
        ))

        if not hasattr(resource_time, "completion"): continue

        data.append(dict(
            Delta = delta(resource_time.completion),
            Count = count,
            Percentage = count / total_resource_count,
            Timestamp = resource_time.completion,
            Name = f"{resource_kind_name} Completed",
            ResourceName = resource_time.name,
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
        if entry.results.test_case_properties.mode == "kueue":
            data += generate_launch_progress_data(entry, "Workload")

        data += generate_launch_progress_data(entry, "Job")

        for key in "creation_time", "pod_scheduled", "container_finished":
            data += generate_pod_progress_data(entry, key)

        df = pd.DataFrame(data)

        fig = go.Figure()
        for name in df.Name.unique():
            df_name = df[df.Name == name]
            fig.add_trace(go.Scatter(x=df_name.Delta,
                                     y=df_name.Count, #Percentage,
                                     fill="tozeroy",
                                     mode='lines',
                                     name=name,
                                     hovertext=df.ResourceName,
                                 ))

        total_pod_count = entry.results.test_case_properties.total_pod_count
        fig.update_yaxes(title="Number of objects")
        fig.update_xaxes(title="Timeline, in minutes after the start time")

        fig.update_layout(title=f"Pod Completion Progress<br>for a total of {total_pod_count} Pods from {entry.results.target_kind_name}s", title_x=0.5)

        #fig.layout.yaxis.tickformat = ',.0%'

        return fig, ""
