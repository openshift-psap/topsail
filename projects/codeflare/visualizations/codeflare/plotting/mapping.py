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
    AppWrappersTimeline()
    AppWrappersInStateTimeline()

def ResourceMappingTimeline_generate_data(entry):
    data = []

    hostnames_index = list(entry.results.nodes_info.keys()).index

    for pod_time in entry.results.pod_times:
        pod_name = pod_time.pod_friendly_name

        hostname = pod_time.hostname or "No hostname"
        shortname = hostname.replace(".compute.internal", "").replace(".us-west-2", "").replace(".ec2.internal", "")

        finish = getattr(pod_time, "container_finished", False) or entry.results.test_start_end_time.end

        try:
            hostname_index = hostnames_index(hostname)
        except ValueError:
            hostname_index = -1

        data.append(dict(
            Time = pod_time.start_time,
            Inc = 1,
            NodeName = f"Node {hostname_index}<br>{shortname}",
            PodName = pod_name,
        ))

        data.append(dict(
            Time = finish,
            Inc = -1,
            NodeName = f"Node {hostname_index}<br>{shortname}",
            PodName = pod_name,
        ))

    if not data:
        return []

    df = pd.DataFrame(data).sort_values(by="Time")
    YOTA = datetime.timedelta(microseconds=1)
    node_pod_count = defaultdict(int)
    data = []
    for index, row in df.iterrows():
        data.append(dict(
            Time = row.Time - YOTA,
            Count = node_pod_count[row.NodeName],
            NodeName = row.NodeName,
        ))
        node_pod_count[row.NodeName] += row.Inc
        data.append(dict(
            Time = row.Time,
            Count = node_pod_count[row.NodeName],
            NodeName = row.NodeName,
        ))

    for node in node_pod_count.keys():
        data.insert(0, dict(
            Time =entry.results.test_start_end_time.start,
            Count = 0,
            NodeName = node,
        ))

        data.append(dict(
            Time =entry.results.test_start_end_time.end,
            Count = 0,
            NodeName = node,
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

        for entry in common.Matrix.all_records(settings, setting_lists):
            data = ResourceMappingTimeline_generate_data(entry)

        if not data:
            return None, "Not data available ..."

        df = pd.DataFrame(data)

        fig = go.Figure()
        for name in df.NodeName.unique():
            df_name = df[df.NodeName == name]
            fig.add_trace(go.Scatter(x=df_name.Time,
                                     y=df_name.Count,
                                     fill="tozeroy",
                                     mode='lines',
                                     name=name,
                                 ))
        fig.update_layout(showlegend=True)

        fig.update_layout(title=f"Timeline of the Pod Count running on the cluster nodes", title_x=0.5,)
        fig.update_layout(yaxis_title="Pod count")
        fig.update_layout(xaxis_title=f"Timeline (by date)")

        return fig, ""

def generateAppWrappersTimeline(entry):
    data = []
    for resource_name, resource_times in entry.results.resource_times.items():
        if resource_times.kind != "AppWrapper": continue

        current_name = None
        current_start = None
        for condition_name, condition_ts in resource_times.aw_conditions.items():
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

class AppWrappersTimeline():
    def __init__(self):
        self.name = "AppWrappers Timeline"
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

        df = pd.DataFrame(generateAppWrappersTimeline(entry))
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
        aw_count = entry.results.test_case_config["aw"]["count"]
        fig.update_layout(title=f"Timeline of the {aw_count} AppWrappers <br>progressing over the different States", title_x=0.5,)
        fig.update_layout(yaxis_title="")
        fig.update_layout(xaxis_title="Timeline (by date)")

        return fig, ""


class AppWrappersInStateTimeline():
    def __init__(self):
        self.name = "AppWrappers in State Timeline"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if common.Matrix.count_records(settings, setting_lists) != 1:
            return {}, "ERROR: only one experiment must be selected"

        for entry in common.Matrix.all_records(settings, setting_lists):
            src_data = generateAppWrappersTimeline(entry)

        if not src_data:
            return None, "Not data available ..."

        histogram_data = []

        def mytruncate(x, base=5):
            return base * int(x/base)

        YOTA = datetime.timedelta(microseconds=1)
        TIME_DELTA = 1 # seconds
        for src_entry in src_data:
            current = copy.deepcopy(src_entry["Start"])
            current = current.replace(second=mytruncate(current.second, TIME_DELTA)).replace(microsecond=0)
            current += datetime.timedelta(seconds=TIME_DELTA) # avoid counting the state twice

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

        fig.update_layout(title=f"Count of the number of AppWrappers <br>in the different States", title_x=0.5,)
        fig.update_layout(yaxis_title="AppWrappers count")
        fig.update_layout(xaxis_title=f"Timeline (by date, by step of {TIME_DELTA}s)")

        return fig, ""
