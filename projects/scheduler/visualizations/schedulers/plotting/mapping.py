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
    ResourceMappingTimeline()
    ResourcesTimeline()
    ResourcesInStateTimeline()



def ResourceMappingTimeline_generate_raw_data(entry):
    data = []

    start_time = entry.results.test_start_end_time.start

    hostnames_index = list(entry.results.nodes_info.keys()).index

    def delta(ts):
        return (ts - start_time).total_seconds() / 60

    for pod_time in entry.results.pod_times:
        pod_name = pod_time.pod_friendly_name

        hostname = pod_time.hostname or "No hostname"
        shortname = hostname.replace(".compute.internal", "").replace(".us-west-2", "").replace(".ec2.internal", "")

        finish = getattr(pod_time, "container_finished", False) or entry.results.test_start_end_time.end

        try:
            hostname_index = hostnames_index(hostname)
        except ValueError:
            hostname_index = -1

        node_name = f"Node {hostname_index}<br>{shortname}"

        data.append(dict(
            Time = pod_time.start_time,
            Delta = delta(pod_time.start_time),
            Inc = 1,
            NodeName = node_name,
            PodName = pod_name,
        ))

        data.append(dict(
            Time = finish,
            Delta = delta(finish),
            Inc = -1,
            NodeName = node_name,
            PodName = pod_name,
        ))

    return data


def ResourceMappingTimeline_generate_data_by_node(entry):
    raw_data = ResourceMappingTimeline_generate_raw_data(entry)
    if not raw_data:
        return []

    start_time = entry.results.test_start_end_time.start
    def delta(ts):
        return (ts - start_time).total_seconds() / 60

    df = pd.DataFrame(raw_data).sort_values(by="Time")
    YOTA = datetime.timedelta(microseconds=1)
    node_pod_count = defaultdict(int)
    data = []

    node_names = set()
    for index, row in df.iterrows():
        node_names.add(row.NodeName)

    for index, row in df.iterrows():
        for node_name in node_names:
            data.append(dict(
                Time = row.Time - YOTA,
                Delta = delta(row.Time - YOTA),
                Count = node_pod_count[node_name],
                NodeName = node_name,
            ))
        node_pod_count[row.NodeName] += row.Inc
        for node_name in node_names:
            data.append(dict(
                Time = row.Time,
                Delta = delta(row.Time),
                Count = node_pod_count[node_name],
                NodeName = node_name,
            ))

    for node in node_pod_count.keys():
        data.insert(0, dict(
            Time = entry.results.test_start_end_time.start,
            Delta = delta(entry.results.test_start_end_time.start),
            Count = 0,
            NodeName = node,
        ))

        data.append(dict(
            Time = entry.results.test_start_end_time.end,
            Delta = delta(entry.results.test_start_end_time.end),
            Count = 0,
            NodeName = node,
        ))

    return data


def ResourceMappingTimeline_generate_data_by_pod(entry):
    raw_data = ResourceMappingTimeline_generate_raw_data(entry)
    if not raw_data:
        return []

    df = pd.DataFrame(raw_data).sort_values(by="Time")

    start_time = entry.results.test_start_end_time.start
    def delta(ts):
        return (ts - start_time).total_seconds() / 60

    pod_names = set()
    pod_node = {}
    for index, row in df.iterrows():
        pod_names.add(row.PodName)
        if row.PodName not in pod_node:
            pod_node[row.PodName] = row.NodeName

    YOTA = datetime.timedelta(microseconds=1)
    pod_states = defaultdict(int)
    data = []
    for index, row in df.iterrows():
        for pod_name in pod_names:
            data.append(dict(
                Delta = delta(row.Time - YOTA),
                PodName = pod_name,
                Count = pod_states[pod_name],
                NodeName = pod_node[pod_name],
            ))

        pod_states[row.PodName] += row.Inc

        for pod_name in pod_names:
            data.append(dict(
                Delta = delta(row.Time + YOTA),
                PodName = pod_name,
                Count = pod_states[pod_name],
                NodeName = pod_node[pod_name],
            ))

    return data

class ResourceMappingTimeline():
    def __init__(self):
        self.name = "Resource Mapping Timeline"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if common.Matrix.count_records(settings, setting_lists) != 1:
            return {}, "ERROR: only one experiment must be selected"

        cfg__all_at_one = cfg.get("all_at_once", False)
        cfg__by_pod = cfg.get("by_pod", False)

        for entry in common.Matrix.all_records(settings, setting_lists):
            pass # entry is set

        if cfg__by_pod:
            data = ResourceMappingTimeline_generate_data_by_pod(entry)
        else:
            data = ResourceMappingTimeline_generate_data_by_node(entry)

        if not data:
            return None, "Not data available ..."

        df = pd.DataFrame(data)

        if cfg__all_at_one:
            fig = px.area(df, x="Delta", y="Count", color="PodName" if cfg__by_pod else "NodeName")
        else:
            fig = go.Figure()
            for name in df.NodeName.unique():
                df_name = df[df.NodeName == name]
                fig.add_trace(go.Scatter(x=df_name.Delta,
                                        y=df_name.Count,
                                         fill="tozeroy",
                                         mode='lines',
                                         name=name,
                                         ))
            fig.update_layout(showlegend=True)

        fig.update_layout(title=f"Timeline of the {entry.results.target_kind_name}'s Pod count<br>running on the cluster nodes", title_x=0.5,)
        fig.update_layout(yaxis_title="Pod count")
        fig.update_layout(xaxis_title=f"Timeline, in minutes after the start time")

        return fig, ""

def generateResourcesTimeline(entry):
    data = []
    for resource_name, resource_times in entry.results.resource_times.items():
        if resource_times.kind not in ("AppWrapper", "Workload"): continue

        current_name = None
        current_start = None
        for condition_name, condition_ts in resource_times.conditions.items():
            if current_name:
                data.append(dict(
                    Name=resource_times.name,
                    StateTransition=f"{current_name} -> {condition_name}",
                    State=f"{current_name}",
                    Start=current_start,
                    Finish=condition_ts,
                ))
            current_name = condition_name
            current_start = condition_ts

        if current_name:
            data.append(dict(
                Name=resource_times.name,
                State=current_name,
                StateTransition=current_name,
                Start=current_start,
                Finish=entry.results.test_start_end_time.end, # last state lives until the end of the test
            ))
    return data

class ResourcesTimeline():
    def __init__(self):
        self.name = "Resources Timeline"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if common.Matrix.count_records(settings, setting_lists) != 1:
            return {}, "ERROR: only one experiment must be selected"


        for entry in common.Matrix.all_records(settings, setting_lists):
            pass

        count = entry.results.test_case_properties.count
        if count > 300:
            return None, f"Too many objects ({count})for this plot ...."

        df = pd.DataFrame(generateResourcesTimeline(entry))
        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["Name"])

        fig = px.timeline(df,
                          x_start="Start", x_end="Finish",
                          y="Name", color="State")

        for fig_data in fig.data:
            if fig_data.x[0].__class__ is datetime.timedelta:
                # workaround for Py3.9 error:
                # TypeError: Object of type timedelta is not JSON serializable
                fig_data.x = [v.total_seconds() * 1000 for v in fig_data.x]

        fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
        fig.update_layout(barmode='stack')

        fig.update_layout(title=f"Timeline of the {count} {entry.results.target_kind_name}s <br>progressing over the different States", title_x=0.5,)
        fig.update_layout(yaxis_title="")
        fig.update_layout(xaxis_title="Timeline (by date)")

        return fig, ""


class ResourcesInStateTimeline():
    def __init__(self):
        self.name = "Resources in State Timeline"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if common.Matrix.count_records(settings, setting_lists) != 1:
            return {}, "ERROR: only one experiment must be selected"

        for entry in common.Matrix.all_records(settings, setting_lists):
            src_data = generateResourcesTimeline(entry)

        if not src_data:
            return None, "Not data available ..."

        histogram_data = []

        def mytruncate(x, base=5):
            return base * int(x/base)

        src_df = pd.DataFrame(src_data).sort_values(by=["Start"])

        YOTA = datetime.timedelta(microseconds=1)
        TIME_DELTA = 1 # seconds
        for src_row in src_df.values:
            src_entry = dict(zip(src_df.keys(), src_row))
            current = copy.deepcopy(src_entry["Start"])
            current = current.replace(second=mytruncate(current.second, TIME_DELTA)).replace(microsecond=0)
            current += datetime.timedelta(seconds=TIME_DELTA) # avoid counting the state twice

            if current >= src_entry["Finish"]:
                current = src_entry["Finish"] - datetime.timedelta(seconds=TIME_DELTA)

            while current < src_entry["Finish"]:
                histogram_data.append(dict(
                    State = src_entry["State"],
                    Time = current,
                    Count = 1,
                ))
                histogram_data.append(dict(
                    State = src_entry["State"],
                    Time = current + datetime.timedelta(seconds=TIME_DELTA) - YOTA,
                    Count = 1,
                ))

                current += datetime.timedelta(seconds=TIME_DELTA)

        df = pd.DataFrame(histogram_data).groupby(["State", "Time"]).count().reset_index()
        df = df.sort_values(by=["Time"]) # "ensures" that the states are ordered by appearance time

        fig = px.area(df,
                      x="Time", y="Count",
                      color="State",
                      )

        for fig_data in fig.data:
            if fig_data.x[0].__class__ is datetime.timedelta:
                # workaround for Py3.9 error:
                # TypeError: Object of type timedelta is not JSON serializable
                fig_data.x = [v.total_seconds() * 1000 for v in fig_data.x]

        fig.update_layout(title=f"Count of the number of {entry.results.target_kind_name} <br>in the different States", title_x=0.5,)
        fig.update_layout(yaxis_title=f"{entry.results.target_kind_name} count")
        fig.update_layout(xaxis_title=f"Timeline (by date, by step of {TIME_DELTA}s)")

        return fig, ""
