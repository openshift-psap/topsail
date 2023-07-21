from collections import defaultdict

import statistics as stats

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    PodTimes()
    ExecutionTimeline()

def generatePodTimes(entry):
    data = []
    for p in entry.results.pods_info:
        workload_phase = { 
            "Start": p.creation_time,
            "End": p.container_finished,
            "Duration": (p.container_finished - p.creation_time).seconds,
            "Pod": p.pod_name,
            "Node": p.hostname,
            "Workload": p.workload
        }
        data.append(workload_phase)

    return data

def generatePodTimeline(entry):
    data = []
    for p in entry.results.pods_info:
        startup_phase = {
            "Start": p.creation_time,
            "End": p.container_started,
            "Creation": p.creation_time,
            "Duration": (p.container_started - p.creation_time).seconds,
            "Pod": p.pod_name,
            "Node": p.hostname,
            "Workload": p.workload,
            "Phase": "Preparing"
        }
        data.append(startup_phase)
        workload_phase = { 
            "Start": p.container_started,
            "End": p.container_finished,
            "Creation": p.creation_time,
            "Duration": (p.container_finished - p.container_started).seconds,
            "Pod": p.pod_name,
            "Node": p.hostname,
            "Workload": p.workload,
            "Phase": "Running"
        }
        data.append(workload_phase)

    return data

class PodTimes():
    def __init__(self):
        self.name = f"Pod time distribution"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        cnt = common.Matrix.count_records(settings, setting_lists)
        if cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            break

        cfg__workload = cfg.get("workload", False)
        data = filter(lambda pod: pod["Workload"] == cfg__workload, generatePodTimes(entry))

        if not data:
            return None, "No data to plot ..."

        df = pd.DataFrame(data)

        fig = px.histogram(df, x="Duration",
                           marginal="box",
                           barmode="overlay",
                           hover_data=df.columns)
        fig.update_layout(xaxis_title="Pod time to complete (seconds)")

        title = f"Distribution of the runtime for {cfg__workload} pods"

        fig.update_layout(title=title, title_x=0.5)

        msg = []

        return fig, msg

class ExecutionTimeline():
    def __init__(self):
        self.name = "Pod execution timeline"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        print(settings)
        cnt = common.Matrix.count_records(settings, setting_lists)
        if cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            break

        data = generatePodTimeline(entry)

        if not data:
            return None, "No data to plot ..."

        df = pd.DataFrame(data).sort_values(by=["Start"])
        print(df)

        fig = px.timeline(df, x_start="Start",
                          x_end="End", y="Pod",
                          color="Phase",
                          hover_data=["Start", "End", "Duration", "Pod", "Node"],
                          category_orders={"Pod": df["Pod"].tolist()})
        fig.update_layout(xaxis_title="Time")

        title = f"Pod execution timeline"

        fig.update_layout(title=title, title_x=0.5)

        msg = []

        return fig, msg
