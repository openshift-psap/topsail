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


def ResourceMappingTimeline_generate_data(entry, workload):
    data = []

    hostnames_index = list(entry.results.nodes_info.keys()).index

    for pod_time in entry.results.pods_info:
        if workload and pod_time.workload != workload:
            continue

        pod_name = pod_time.pod_name

        hostname = pod_time.hostname or "No hostname"
        shortname = hostname.replace(".compute.internal", "").replace(".us-west-2", "").replace(".ec2.internal", "")

        finish = getattr(pod_time, "container_finished", False)
        if not finish:
            logging.error(f"Pod '{pod_name}' did not finish :/")
            continue

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
        continue
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

        cfg__workload = cfg.get("workload", False)

        for entry in common.Matrix.all_records(settings, setting_lists):
            data = ResourceMappingTimeline_generate_data(entry, cfg__workload)

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

        fig.update_layout(title=f"Timeline of the {cfg__workload or ''}Pod Count running on the cluster nodes with the {entry.settings.scheduler} scheduler", title_x=0.5,)
        fig.update_layout(yaxis_title="Pod count")
        fig.update_layout(xaxis_title=f"Timeline (by date)")

        return fig, ""
