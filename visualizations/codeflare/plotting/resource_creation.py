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

        data = []
        for pod_time in entry.results.pod_times:
            data.append({
                "Resource": f"Pod/{pod_time.pod_friendly_name}",
                "Create Time": pod_time.creation_time,
                "Node": "None",
            })

        for resource_name, creation_time in entry.results.resource_times.items():
            data.append({
                "Resource": resource_name,
                "Create Time": creation_time,
                "Node": "N/A",
            })

        if not data:
            return None, "No data available"

        df = pd.DataFrame(data).sort_values(by=["Create Time"], ascending=True)

        fig = px.line(df, x="Create Time", y="Resource", color="Node", title="Resource creation time")

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

        cfg__dspa_only = cfg.get("dspa_only", False)
        cfg__pipeline_task_only = cfg.get("pipeline_task_only", False)

        mapping = {
            "DataSciencePipelinesApplication/sample": {
                "Deployment": ["ds-pipeline-persistenceagent-sample", "ds-pipeline-sample", "ds-pipeline-scheduledworkflow-sample", "ds-pipeline-ui-sample", "mariadb-sample"],
            },
        }

        data = []
        for user_idx, user_data in entry.results.user_data.items():

            for base_name, dependencies in mapping.items():
                if cfg__pipeline_task_only:
                    continue

                try:
                    base_time = user_data.resource_times[base_name]
                except KeyError: continue

                for dep_kind, dep_names in dependencies.items():
                    for dep_name in dep_names:
                        try: dep_time = user_data.resource_times[f"{dep_kind}/{dep_name}"]
                        except KeyError: continue

                        duration = (dep_time - base_time).total_seconds()

                        data.append({
                            "Base": base_name,
                            "Mapping Name": f"{base_name} -> {dep_kind}/{dep_name}",
                            "Duration": duration,
                            "User Index": user_idx,
                            "User Name": f"User #{user_idx:03d}",
                        })

            for pipelinerun_name in [k for k in user_data.resource_times.keys() if k.startswith("PipelineRun/")]:
                if cfg__dspa_only:
                    continue

                base_name = pipelinerun_name
                base_time = user_data.resource_times[base_name]

                for pod_time in user_data.pod_times:
                    if not pod_time.is_pipeline_task: continue

                    dep_kind = "Pod"
                    dep_name = pod_time.pod_friendly_name
                    dep_time = pod_time.creation_time

                    duration = (dep_time - base_time).total_seconds()

                    data.append({
                        "Base": base_name,
                        "Mapping Name": f"{base_name} -> {dep_kind}/{dep_name}",
                        "Duration": duration,
                        "User Index": user_idx,
                        "User Name": f"User #{user_idx:03d}",
                    })

        if not data:
            return None, "No data available"

        df = pd.DataFrame(data).sort_values(by=["User Index", "Base"], ascending=True)

        fig = px.line(df, x="Duration", y="User Name", color="Mapping Name", title="Resource creation duration")

        fig.update_layout(xaxis_title="Resource creation duration, in seconds")
        fig.update_layout(yaxis_title="User index")
        fig.update_yaxes(autorange="reversed") # otherwise users are listed from the bottom up
        fig.update_xaxes(range=[0, df["Duration"].max()*1.1])

        what = ""
        if cfg__dspa_only:
            what = "DSPApplication "
        if cfg__pipeline_task_only:
            what = "Pipelines "
        title = f"Duration of the {what}Resource Creation"

        fig.update_layout(title=title, title_x=0.5,)

        return fig, ""
