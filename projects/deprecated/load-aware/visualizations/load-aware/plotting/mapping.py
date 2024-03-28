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
    MappingDistribution()

def ResourceMappingTimeline_generate_metric_data(entry, _metric_name, cluster_role="sutest"):
    data = []
    for _metric in entry.results.metrics[cluster_role].get(_metric_name):
        metric_labels = _metric.metric

        for metric in _metric.values:
            data.append(dict(
                Instance = metric_labels["instance"],
                Time = datetime.datetime.utcfromtimestamp(metric[0]),
                Value = float(metric[1]),
            ))

    return data

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
            Instance = hostname,
        ))

        data.append(dict(
            Time = finish,
            Inc = -1,
            NodeName = f"Node {hostname_index}<br>{shortname}",
            PodName = pod_name,
            Instance = hostname,
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
            Instance = row.Instance,
        ))
        node_pod_count[row.NodeName] += row.Inc
        data.append(dict(
            Time = row.Time,
            Count = node_pod_count[row.NodeName],
            NodeName = row.NodeName,
            Instance = row.Instance,
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
        cfg__instance = cfg.get("instance", False)

        for entry in common.Matrix.all_records(settings, setting_lists):
            data = ResourceMappingTimeline_generate_data(entry, cfg__workload)
            metric_data = ResourceMappingTimeline_generate_metric_data(entry, "Sutest Node CPU Utilisation rate")

        if not data:
            return None, "Not data available ..."

        df = pd.DataFrame(data)
        df_metric = pd.DataFrame(metric_data)

        from plotly.subplots import make_subplots
        fig = make_subplots(specs=[[{"secondary_y": True}]])


        for idx, instance_name in enumerate(df.Instance.unique()):
            color = px.colors.qualitative.Plotly[idx % len(px.colors.qualitative.Plotly)]

            if cfg__instance and cfg__instance != instance_name:
                continue

            df_name = df[df.Instance == instance_name]
            name = df_name.NodeName.unique()[0]
            fig.add_trace(go.Scatter(x=df_name.Time,
                                     y=df_name.Count,
                                     fill="tozeroy",
                                     mode='lines',
                                     line_color=color,
                                     name="Pod count",
                                     legendgroup=name,
                                     legendgrouptitle_text=name,
                                 ))
            if df_metric.empty:
                continue
            if not cfg__instance:
                continue

            df_metric_name = df_metric[df_metric.Instance == instance_name]

            fig.add_trace(go.Scatter(x=df_metric_name.Time,
                                     y=df_metric_name.Value,
                                     mode='lines',
                                     line_color=color,
                                     name="Node CPU",
                                     legendgroup=name,
                                     legendgrouptitle_text=name,
                                     ),
                          secondary_y=True,
                          )

        fig.update_layout(showlegend=True)

        fig.update_layout(title=f"Timeline of the {cfg__workload or ''} Pod Count running on the cluster nodes with the {entry.settings.scheduler} scheduler", title_x=0.5,)
        fig.update_layout(yaxis_title="Pod count")
        fig.update_layout(xaxis_title=f"Timeline (by date)")

        fig.update_yaxes(title_text="Node CPU utilization rate [1min]", secondary_y=True, range=[0, 1])

        return fig, ""

def MappingDistribution_generate_data(entry, workload=False):
    test_nodes = {}
    entry_results = entry.results

    data = []

    hostnames_index = list(entry.results.nodes_info.keys()).index

    for pod_time in entry.results.pods_info:
        if workload and pod_time.workload != workload:
            continue

        pod_name = pod_time.pod_name
        pod_index = int(pod_time.pod_name.split("-")[-1].replace("n", ""))

        hostname = pod_time.hostname
        shortname = hostname.replace(".compute.internal", "").replace(".us-west-2", "")
        hostname_index = hostnames_index(hostname)

        try:
            instance_type = entry.results.nodes_info[hostname].instance_type
        except (AttributeError, KeyError):
            instance_type = ""

        data.append(dict(
            PodIndex = pod_index,
            NodeIndex = f"Node {hostname_index}",
            NodeName = f"Node {hostname_index}<br>{shortname}" + (f"<br>{instance_type}" if instance_type != "N/A" else ""),
            Count=1,
            Workload=pod_time.workload,
        ))

    return data


class MappingDistribution():
    def __init__(self):
        self.name = "Pod/Node distribution"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if common.Matrix.count_records(settings, setting_lists) != 1:
            return {}, "ERROR: only one experiment must be selected"

        cfg__workload = cfg.get("workload", False)

        df = None
        for entry in common.Matrix.all_records(settings, setting_lists):
            df = pd.DataFrame(MappingDistribution_generate_data(entry, cfg__workload))

        if df.empty:
            return None, "Nothing to plot (no data)"

        # sort by UserIndex to improve readability
        df = df.sort_values(by=["PodIndex", "NodeName"])

        what = f"<b>{cfg__workload}</b> " if cfg__workload else ""

        fig = px.bar(df, x="NodeName", y="Count", color="PodIndex",
                     title=f"Distribution of {'<b>all</b> ' if not cfg__workload else ''}the {what}Pods on the nodes")

        fig.update_layout(title_x=0.5,)
        fig.update_layout(xaxis_title="")
        fig.update_layout(yaxis_title="Pod count")
        fig.update_yaxes(tick0=0, dtick=1)
        return fig, ""
