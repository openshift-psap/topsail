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
    NodeResourceAllocation()

def get_data(entry, cfg__instance, memory=False, cpu=False, gpu=False):
    cluster_role = "sutest"

    value_divisor = 1024*1024*1024 if memory else 1
    if memory:
        resource_name = "memory"
    elif cpu:
        resource_name = "cpu"
    elif gpu:
        resource_name = "nvidia.com/gpu"
        total_metric_name = f"{cluster_role.title()} Control Plane Node Total GPU"

    request_metric_name = "Sutest Control Plane Node Resource Request"
    limit_metric_name = "Sutest Control Plane Node Resource Limit"

    data = []

    if not entry.results.metrics:
        logging.error("No metric available ...")
        return pd.DataFrame([])

    for metric in entry.results.metrics[cluster_role][request_metric_name]:
        if cfg__instance != metric.metric.get("node", ""): continue
        if resource_name != metric.metric.get("resource", ""): continue

        for ts, val in metric.values.items():
            data.append(
                dict(type="3. Request",
                     ts=datetime.datetime.fromtimestamp(ts),
                     value=float(val) / value_divisor,
                     )
            )

    for metric in entry.results.metrics[cluster_role][limit_metric_name]:
        if cfg__instance != metric.metric.get("node", ""): continue
        if resource_name != metric.metric.get("resource", ""): continue

        for ts, val in metric.values.items():
            data.append(
                dict(type="2. Limit",
                     ts=datetime.datetime.fromtimestamp(ts),
                     value=float(val) / value_divisor,
                     )
            )

    if not data:
        return pd.DataFrame([])

    node = entry.results.nodes_info.get(cfg__instance)
    if not node:
        logging.error(f"No information about node '{cfg_instance}'")
    else:
        df = pd.DataFrame(data)
        start_ts = pd.DataFrame(data)["ts"].min()
        end_ts = pd.DataFrame(data)["ts"].max()

        total_value = entry.results.nodes_info[cfg__instance].allocatable.__dict__[resource_name] / value_divisor
        data += [
            dict(type="1. Total", ts=start_ts, value=total_value),
            dict(type="1. Total", ts=end_ts, value=total_value),
        ]

    return pd.DataFrame(data).sort_values(by=["type", "ts"])

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

        cfg__instance = cfg.get("instance", "")
        if not cfg__instance:
            return None, "No 'instance' parameter received"

        cfg__what = cfg.get("what", "")

        memory = False
        cpu = False
        gpu = False
        if not cfg__what:
            return None, "No 'what' parameter received"

        elif cfg__what == "memory":
            memory = True
        elif cfg__what == "cpu":
            cpu = True
        elif cfg__what == "gpu":
            gpu = True
        else:
            return None, f"Invalid 'what' parameter received ({what})"

        df = get_data(entry, cfg__instance, memory=memory, gpu=gpu, cpu=cpu)

        if df.empty:
            return None, "Not data available ..."

        fig = px.line(df, x="ts", y="value", color='type')
        if memory:
            fig.update_yaxes(title="Memory usage (in Gi)")
            title_what = "Memory"
        elif cpu:
            fig.update_yaxes(title="CPU usage (in core)")
            title_what = "CPU"
        elif gpu:
            fig.update_yaxes(title="GPU usage (in GPU count)")
            title_what = "GPU"

        fig.update_xaxes(title="Timeline")
        fig.update_layout(title=f"<b>{title_what} usage</b><br>of Node '{cfg__instance}'", title_x=0.5)
        fig.update_yaxes(range=[0, df["value"].max()*1.1])

        return fig, ""
