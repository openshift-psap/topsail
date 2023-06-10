from collections import defaultdict
import re
import logging
import datetime

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    MappingTimeline("Pod/Node timeline")


def generate_data(entry, cfg):
    data = []

    hostnames_index = list(entry.results.nodes_info.keys()).index

    for pod_time in entry.results.pod_times:
        user_idx = pod_time.user_index

        pod_name = pod_time.pod_name
        hostname = pod_time.hostname

        shortname = hostname.replace(".compute.internal", "").replace(".us-west-2", "").replace(".ec2.internal", "")
        if pod_time.container_finished:
            finish = pod_time.container_finished
        else:
            finish = entry.results.tester_job.completion_time

        user_index = f"User #{user_idx:02d}"
        data.append(dict(
            UserIndex = user_index,
            PodName = f"{pod_name} -- {user_index}",
            UserIdx = user_idx,
            PodStart = pod_time.start_time,
            PodFinish = finish,
            NodeIndex = f"Node {hostnames_index(hostname)}",
            NodeName = f"Node {hostnames_index(hostname)}<br>{shortname}",
            Count=1,
        ))

    return data

class MappingTimeline():
    def __init__(self, name):
        self.name = name
        self.id_name = name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if common.Matrix.count_records(settings, setting_lists) != 1:
            return {}, "ERROR: only one experiment must be selected"

        cfg__force_order_by_user_idx = cfg.get("force_order_by_user_idx", False)

        df = None
        for entry in common.Matrix.all_records(settings, setting_lists):
            df = pd.DataFrame(generate_data(entry, cfg))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["PodStart"])

        fig = px.timeline(df,
                          x_start="PodStart", x_end="PodFinish",
                          y="PodName", color="UserIndex")

        for fig_data in fig.data:
            if fig_data.x[0].__class__ is datetime.timedelta:
                # workaround for Py3.9 error:
                # TypeError: Object of type timedelta is not JSON serializable
                fig_data.x = [v.total_seconds() * 1000 for v in fig_data.x]

        fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
        fig.update_layout(barmode='stack', title=f"Mapping of the User Pods on the nodes", title_x=0.5,)
        fig.update_layout(yaxis_title="")
        fig.update_layout(xaxis_title="Timeline (by date)")

        return fig, ""
