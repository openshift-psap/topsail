from collections import defaultdict
import datetime
import statistics as stats

from dash import html
import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    ResourceCreationTimeline()
    ResourceCreationDelay()

def generateData(entry):
    data = []
    for pod_time in entry.results.pod_times:
        data.append({
            "Resource Name": pod_time.pod_friendly_name,
            "Create Time": pod_time.creation_time,
            "Kind": "Pod",
        })

    for resource_name, resource_times in entry.results.resource_times.items():
        data.append({
            "Resource Name": resource_times.name if resource_times.kind != "Workload" else resource_times.parent_job_name,
            "Create Time": resource_times.creation,
            "Kind": resource_times.kind,
        })
    return data


class ResourceCreationTimeline():
    def __init__(self):
        self.name = "Resource Creation Timeline"
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


        data = generateData(entry)

        if not data:
            return None, "No data available"

        df = pd.DataFrame(data).sort_values(by=["Resource Name"], ascending=True)

        fig = px.line(df, x="Create Time", y="Resource Name", color="Kind", title="Resource creation time")

        fig.update_layout(xaxis_title="Timeline (in seconds)")
        fig.update_layout(yaxis_title="")
        fig.update_yaxes(autorange="reversed") # otherwise users are listed from the bottom up

        what = ""

        title = f"{what}Resources Creation Timeline"

        fig.update_layout(title=title, title_x=0.5,)

        return fig, ""


class ResourceCreationDelay():
    def __init__(self):
        self.name = "Resource Creation Delay"
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

        src_data = generateData(entry)

        if not src_data:
            return None, "No data available"

        MAPPINGS = {}
        if "kueue" in common.Matrix.settings["mode"]:
            MAPPINGS["Job"] = "Workload"
            MAPPINGS["Workload"] = "Pod"
        elif "job" in common.Matrix.settings["mode"]:
            MAPPINGS["Job"] = "Pod"
        elif "mcad" in common.Matrix.settings["mode"]:
            MAPPINGS["AppWrapper"] = "Job"
            MAPPINGS["Job"] = "Pod"

        mapping = defaultdict(dict)
        for timing in src_data:
            mapping[timing["Resource Name"]][timing["Kind"]] = timing["Create Time"]

        data = []
        for name, mapping_entry in mapping.items():
            for src_kind, dst_kind in MAPPINGS.items():
                src_time = mapping[name].get(src_kind)
                dst_time = mapping[name].get(dst_kind)
                if None in (src_time, dst_time): continue

                duration = (dst_time - src_time).total_seconds()
                data.append({
                    "Mapping Name": f"{src_kind} -> {dst_kind}",
                    "Duration": duration,
                    "Resource Name": name,
            })


        if not data:
            return None, "No data available"

        df = pd.DataFrame(data).sort_values(by=["Resource Name"], ascending=True)

        fig = px.line(df, x="Duration", y="Resource Name", color="Mapping Name", title="Resource creation duration")

        fig.update_layout(xaxis_title="Resource creation duration, in seconds")
        fig.update_layout(yaxis_title="Resource Name")
        fig.update_yaxes(autorange="reversed") # otherwise users are listed from the bottom up
        fig.update_xaxes(range=[0, df["Duration"].max()*1.1])

        title = f"Duration of the Resource Creation"

        fig.update_layout(title=title, title_x=0.5,)

        return fig, ""
