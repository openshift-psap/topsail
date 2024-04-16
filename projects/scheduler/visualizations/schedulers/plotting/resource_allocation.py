from collections import defaultdict
import datetime
import statistics as stats
import logging

from dash import html
import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
import plotly.subplots as sp

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    NodeResourceAllocation()

def get_data(entry, node, what):
    cluster_role = "sutest"

    value_divisor = 1024*1024*1024 if what == "memory" else 1
    if what == "memory":
        resource_name = "memory"
    elif what == "cpu":
        resource_name = "cpu"
    elif what == "gpu":
        resource_name = "nvidia.com/gpu"
        total_metric_name = f"{cluster_role.title()} Control Plane Node Total GPU"

    request_metric_name = "Sutest Control Plane Node Resource Request"
    limit_metric_name = "Sutest Control Plane Node Resource Limit"

    data = []

    if not entry.results.metrics:
        logging.error("No metric available ...")
        return pd.DataFrame([])

    for metric in entry.results.metrics[cluster_role][request_metric_name]:
        if metric.metric.get("node", "") != node.name: continue
        if resource_name != metric.metric.get("resource", ""): continue

        total_value = node.allocatable.__dict__[resource_name] / value_divisor
        for ts, val in metric.values.items():
            requested = float(val) / value_divisor
            available = total_value - requested

            data.append(dict(
                type=f"2. Available",
                ts=datetime.datetime.fromtimestamp(ts),
                value=available,
            ))

            data.append(dict(
                type=f"1. Requested",
                ts=datetime.datetime.fromtimestamp(ts),
                value=requested,
            ))

    return data


class NodeResourceAllocation():
    def __init__(self):
        self.name = "Node Resource Allocation"
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

        cfg__what = cfg.get("what", "")

        if not cfg__what:
            return None, "No 'what' parameter received"

        elif cfg__what not in ("memory", "cpu", "gpu"):
            return None, f"Invalid 'what' parameter received ({cfg__what})"

        subplots = []
        for node_name in sorted(entry.results.nodes_info):
            node = entry.results.nodes_info[node_name]
            if node.control_plane: continue

            data = get_data(entry, node, cfg__what)

            df = pd.DataFrame(data)
            if df.empty:
                continue

            df = df.sort_values(by=["type", "ts"])

            sub_fig = px.area(df, x="ts", y="value", color='type')

            subplots.append(list(sub_fig["data"]))

        if not subplots:
            return None, "No thing to show"

        fig = sp.make_subplots(rows=len(subplots), cols=1, shared_xaxes=True)
        for idx, subplot in enumerate(subplots):
            for trace in subplot:
                fig.append_trace(trace, row=idx+1, col=1)
                if idx != 0:
                    fig.data[-1].showlegend = False

        if cfg__what == "memory":
            title_what = "Memory"
            yaxis_title = "in Gi"
        elif cfg__what == "cpu":
            title_what = "CPU"
            yaxis_title = "in core"
        elif cfg__what == "gpu":
            title_what = "GPU"
            yaxis_title = "in GPU count"

        fig.update_layout(title=f"<b>{title_what} usage</b> of the worker nodes<br>{yaxis_title}", title_x=0.5)
        fig.update_yaxes(range=[0, df["value"].max()*1.1])

        return fig, ""
