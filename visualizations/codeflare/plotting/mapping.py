from collections import defaultdict
import re
import logging
import datetime
import math

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common


def register():
    ResourceMappingTimeline()
    AppWrappersTimeline()

def generate_data(entry, cfg, dspa_only=False, pipeline_task_only=False):
    data = []

    hostnames_index = list(entry.results.nodes_info.keys()).index

    for pod_time in entry.results.pod_times:
        pod_name = pod_time.pod_friendly_name
        hostname = pod_time.hostname

        shortname = hostname.replace(".compute.internal", "").replace(".us-west-2", "").replace(".ec2.internal", "")
        finish = pod_time.container_finished or entry.results.start_end_time[1]

        try:
            hostname_index = hostnames_index(hostname)
        except ValueError:
            hostname_index = -1

        data.append(dict(
            Name = f"Pod/{pod_name}",
            Start = pod_time.start_time,
            Finish = finish,
            Duration = (finish - pod_time.start_time).total_seconds(),
            Type = f"Pod on Node {hostname_index}",
            NodeName = f"Node {hostname_index}<br>{shortname}",
        ))

    for resource_name, resource_times in entry.results.resource_times.items():
        finish = resource_times.completion or entry.results.start_end_time[1]
        data.append(dict(
            Name = resource_name,
            Start = resource_times.creation,
            Finish = finish,
            Duration = (finish - pod_time.start_time).total_seconds(),
            Type = f"{resource_times.kind}s",
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

        df = None
        for entry in common.Matrix.all_records(settings, setting_lists):
            df = pd.DataFrame(generate_data(entry, cfg))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["Start"])

        fig = px.timeline(df,
                          x_start="Start", x_end="Finish",
                          y="Name")

        for fig_data in fig.data:
            if fig_data.x[0].__class__ is datetime.timedelta:
                # workaround for Py3.9 error:
                # TypeError: Object of type timedelta is not JSON serializable
                fig_data.x = [v.total_seconds() * 1000 for v in fig_data.x]

        fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
        fig.update_layout(barmode='stack', title=f"Mapping of the Resources on the nodes", title_x=0.5,)
        fig.update_layout(yaxis_title="")
        fig.update_layout(xaxis_title="Timeline (by date)")

        return fig, ""


class AppWrappersTimeline():
    def __init__(self):
        self.name = "AppWrappers and Pods Timeline"
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

        data = []
        for resource_name, resource_times in entry.results.resource_times.items():
            if resource_times.kind != "AppWrapper": continue

            current_name = None
            current_start = None
            for condition_name, condition_ts in resource_times.aw_conditions.items():
                if current_name:
                    data.append(dict(
                        Name=resource_times.name,
                        State=current_name,
                        Start=current_start,
                        Finish=condition_ts,
                    ))
                current_name = condition_name
                current_start = condition_ts
                # last one, completed, is ignored, as it stays "active" forever

        for pod_time in entry.results.pod_times:
            finish = pod_time.container_finished or entry.results.start_end_time[1]

            data.append(dict(
                Name = f"{pod_time.pod_friendly_name} (Pod)",
                Start = pod_time.start_time,
                Finish = finish,
                State = "Running",
            ))

        df = pd.DataFrame(data)
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
        fig.update_layout(barmode='stack', title=f"Timeline of the AppWrappers and their Pods", title_x=0.5,)
        fig.update_layout(yaxis_title="")
        fig.update_layout(xaxis_title="Timeline (by date)")

        return fig, ""
