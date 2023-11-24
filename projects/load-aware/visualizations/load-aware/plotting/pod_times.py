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
            "Duration": (p.container_finished - p.creation_time).total_seconds(),
            "Pod": p.pod_name,
            "Node": p.hostname,
            "Workload": p.workload
        }
        data.append(workload_phase)

    return data

def generatePodTimeline(entry):
    data = []

    for p in entry.results.pods_info:

        scheduling_phase = {
            "Start": p.creation_time,
            "End": p.pod_scheduled,
            "Creation": p.creation_time,
            "Duration": (p.pod_scheduled - p.creation_time).total_seconds(),
            "Pod": p.pod_name,
            "Node": p.hostname,
            "Workload": p.workload,
            "Phase": "Scheduling"
        }

        data.append(scheduling_phase)
        startup_phase = {
            "Start": p.pod_scheduled,
            "End": p.container_started,
            "Creation": p.creation_time,
            "Duration": (p.container_started - p.pod_scheduled).total_seconds(),
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
            "Phase": f"Running {p.workload}"
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

        df = pd.DataFrame(data)

        if df.empty:
            return None, "No data to plot ..."

        fig = px.histogram(df, x="Duration",
                           marginal="box",
                           barmode="overlay",
                           hover_data=df.columns)
        fig.update_layout(xaxis_title="Pod time to complete (seconds)")

        title = f"Distribution of the runtime for {cfg__workload} pods"

        fig.update_layout(title=title, title_x=0.5)

        msg = []
        
        q1, med, q3 = (0.0, 0.0, 0.0)
        q90 = 0.0
        q100 = 0.0
        if len(df) >= 2:
            q1, med, q3 = stats.quantiles(df.Duration)
            q90 = stats.quantiles(df.Duration, n=10)[8] # 90th percentile
            q100 = df.Duration.max()

        def time(sec):
            if sec < 0.001:
                return f"0 seconds"
            elif sec < 5:
                return f"{sec:.3f} seconds"
            if sec < 20:
                return f"{sec:.1f} seconds"
            elif sec <= 120:
                return f"{sec:.0f} seconds"
            else:
                return f"{sec/60:.1f} minutes"

        msg.append(html.Br())

        msg += [f"The {len(df)} ", html.B([html.Code(cfg__workload), " Pods"]), " took ", html.B(f"between {time(df.Duration.min())} and {time(df.Duration.max())}"), " to run with the ", html.B(entry.settings.scheduler), "scheduler"]
        msg.append(html.Br())
        msg.append(f"25% ran in less than {time(q1)} [Q1]")
        msg.append(html.Br())
        msg.append(f"50% ran in less than {time(med)} (+ {time(med-q1)}) [median]")
        msg.append(html.Br())
        msg.append(f"75% ran in less than {time(q3)} (+ {time(q3-med)}) [Q3]")
        msg.append(html.Br())
        msg.append(f"90% ran in less than {time(q90)} (+ {time(q90-q3)}) [90th quantile]")
        msg.append(html.Br())
        msg.append(f"There are {time(q3 - q1)} between Q1 and Q3.")
        msg.append(html.Br())
        msg.append(f"There are {time(q100 - q3)} between Q3 and Q4.")
        msg.append(html.Br())

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
        cnt = common.Matrix.count_records(settings, setting_lists)
        if cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            break

        data = generatePodTimeline(entry)

        if not data:
            return None, "No data to plot ..."

        df = pd.DataFrame(data).sort_values(by=["Start"])

        fig = px.timeline(df, x_start="Start",
                          x_end="End", y="Pod",
                          color="Phase",
                          hover_data=["Start", "End", "Duration", "Pod", "Node"],
                          category_orders={"Pod": df["Pod"].tolist()})
        fig.update_layout(xaxis_title="Time")

        title = f"Pod execution timeline"

        fig.update_layout(title=title, title_x=0.5)
       
        scheduling_phase = df[df.Phase == "Scheduling"]
        q1, med, q3 = (0, 0, 0) if len(scheduling_phase) < 2 else stats.quantiles(scheduling_phase.Duration)
        sched_min = 0 if len(scheduling_phase) < 1 else scheduling_phase["Duration"].min()
        sched_max = 0 if len(scheduling_phase) < 1 else scheduling_phase["Duration"].max()
        
        msg = []

        def time(sec):
            if sec < 0.001:
                return f"0 seconds"
            elif sec < 5:
                return f"{sec:.3f} seconds"
            if sec < 20:
                return f"{sec:.1f} seconds"
            elif sec <= 120:
                return f"{sec:.0f} seconds"
            else:
                return f"{sec/60:.1f} minutes"

        msg.append(html.Br())
        msg.append(f"Time spend in the scheduling phase across all workloads")
        msg.append(html.Br())
        msg.append(f"Minimum: {time(sched_min)}")
        msg.append(html.Br())
        msg.append(f"25% ran in less than {time(q1)} [Q1]")
        msg.append(html.Br())
        msg.append(f"50% ran in less than {time(med)} (+ {time(med-q1)}) [median]")
        msg.append(html.Br())
        msg.append(f"75% ran in less than {time(q3)} (+ {time(q3-med)}) [Q3]")
        msg.append(html.Br())
        msg.append(f"Maximum: {time(sched_max)}")
        msg.append(html.Br())

        return fig, msg
