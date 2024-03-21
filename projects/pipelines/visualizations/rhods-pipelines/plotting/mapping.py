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
    MappingTimeline("Pod/Node timeline")
    PodLifespanDuration()

def generate_data(entry, cfg, dspa_only=False, pipeline_task_only=False):
    data = []

    hostnames_index = list(entry.results.nodes_info.keys()).index

    for user_idx, user_data in entry.results.user_data.items():
        for pod_time in user_data.pod_times:
            if dspa_only and not pod_time.is_dspa:
                continue
            if pipeline_task_only and not pod_time.is_pipeline_task:
                continue

            logging.info(pod_time)
            pod_name = pod_time.pod_friendly_name
            hostname = pod_time.hostname or ""

            shortname = hostname.replace(".compute.internal", "").replace(".us-west-2", "").replace(".ec2.internal", "")

            if pod_time.start_time:
                start_time = pod_time.start_time
            else:
                start_time = entry.results.tester_job.creation_time

            if pod_time.container_finished:
                finish = pod_time.container_finished
            else:
                finish = entry.results.tester_job.completion_time

            try:
                hostname_index = hostnames_index(hostname)
            except ValueError:
                hostname_index = -1

            user_index = f"User #{user_idx:02d}"
            data.append(dict(
                UserIndex = user_index,
                PodOwner = f"{pod_name} -- {user_index}",
                PodName = pod_name,
                UserIdx = user_idx,
                PodStart = start_time,
                PodFinish = finish,
                Duration = (finish - start_time).total_seconds(),
                NodeIndex = f"Node {hostname_index}",
                NodeName = f"Node {hostname_index}<br>{shortname}",
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

        cfg__dspa_only = cfg.get("dspa_only", False)
        cfg__pipeline_task_only = cfg.get("pipeline_task_only", False)

        df = None
        for entry in common.Matrix.all_records(settings, setting_lists):
            df = pd.DataFrame(generate_data(entry, cfg,
                                            dspa_only=cfg__dspa_only, pipeline_task_only=cfg__pipeline_task_only))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["PodStart"])

        fig = px.timeline(df,
                          x_start="PodStart", x_end="PodFinish",
                          y="PodOwner", color="UserIndex")

        for fig_data in fig.data:
            if fig_data.x[0].__class__ is datetime.timedelta:
                # workaround for Py3.9 error:
                # TypeError: Object of type timedelta is not JSON serializable
                fig_data.x = [v.total_seconds() * 1000 for v in fig_data.x]

        what = ""
        if cfg__dspa_only:
            what = "DSPApplication"

        if cfg__pipeline_task_only:
            what = "Pipelines"

        fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
        fig.update_layout(barmode='stack', title=f"Mapping of the User {what} Pods on the nodes", title_x=0.5,)
        fig.update_layout(yaxis_title="")
        fig.update_layout(xaxis_title="Timeline (by date)")

        return fig, ""


class PodLifespanDuration():
    def __init__(self):
        self.name = "Pod lifespan duration"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if common.Matrix.count_records(settings, setting_lists) != 1:
            return {}, "ERROR: only one experiment must be selected"

        cfg__dspa_only = cfg.get("dspa_only", False)
        cfg__pipeline_task_only = cfg.get("pipeline_task_only", False)

        df = None
        for entry in common.Matrix.all_records(settings, setting_lists):
            df = pd.DataFrame(generate_data(entry, cfg,
                                            dspa_only=cfg__dspa_only, pipeline_task_only=cfg__pipeline_task_only))

        if df.empty:
            return None, "Not data available ..."

        bin_width = 5 # seconds
        nbins = math.ceil((df["Duration"].max() - df["Duration"].min()) / bin_width)
        fig = px.histogram(df, x="Duration", color="PodName", barmode="overlay", nbins=nbins)

        what = ""
        if cfg__dspa_only:
            what = "DSPApplication"

        if cfg__pipeline_task_only:
            what = "Pipelines"

        fig.update_layout( title=f"Lifespan Duration Distribution for User {what} Pods", title_x=0.5,)

        return fig, ""
