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
                "Namespace": pod_time.namespace,
                "Resource": f"Pod/{pod_time.pod_friendly_name}",
                "Create Time": pod_time.creation_time,
                "Kind": "Pod",
                "User Name": f"User {pod_time.user_idx}",
                "User Index": pod_time.user_idx,
            })

        for user_idx, user_data in entry.results.user_data.items():
            for resource_name, resource_times in user_data.resource_times.items():
                data.append({
                    "Namespace" : resource_times.namespace,
                    "Resource": f"{resource_times.kind}/{resource_times.name}",
                    "Create Time": resource_times.creation,
                    "Kind": resource_times.kind,
                    "User Name": f"User {user_idx}",
                    "User Index": user_idx,
                })

        if not data:
            return None, "No data available"

        df = pd.DataFrame(data).sort_values(by=["Create Time"], ascending=True)

        fig = px.scatter(df, x="Create Time", y="Namespace", title="Resource creation time", color="Resource")

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

        cfg__model_id = cfg.get("model_id", None)


        for entry in common.Matrix.all_records(settings, setting_lists):
            pass # entry is set

        models_per_ns = entry.results.test_config.get("tests.scale.models_per_namespace")
        isvc_basename = entry.results.test_config.get("watsonx_serving.inference_service.name")
        serving_runtime_name = entry.results.test_config.get("watsonx_serving.serving_runtime.name")
        mapping = dict()
        mapping[f"ServingRuntime/{serving_runtime_name}"] = []
        for model_id in range(models_per_ns):
            if cfg__model_id is not None and cfg__model_id != model_id: continue

            isvc_name = f"{isvc_basename}-m{model_id}"
            #mapping[f"ServingRuntime/{serving_runtime_name}"].append(f"InferenceService/{isvc_name}")
            mapping[f"InferenceService/{isvc_name}"] = [
                #f"Route/{isvc_name}",
                #f"Configuration/{isvc_name}",
                f"Service/{isvc_name}",
                #f"Revision/{isvc_name}"
            ]

        data = []
        for user_idx, user_data in entry.results.user_data.items():
            for base_name, dependencies in mapping.items():
                try:
                    base_time = user_data.resource_times[base_name].creation
                except KeyError: continue

                for dep_name in dependencies:
                    try: dep_time = user_data.resource_times[dep_name].creation
                    except KeyError: continue

                    duration = (dep_time - base_time).total_seconds()

                    data.append({
                        "Base Time": base_time,
                        "Mapping Name": f"{base_name} -> {dep_name}",
                        "Duration": duration,
                        "User Index": user_idx,
                        "User Name": f"User #{user_idx:03d}",
                    })

        if not data:
            return None, "No data available"

        df = pd.DataFrame(data).sort_values(by=["Duration"], ascending=True)

        fig = px.line(df, x="Duration", y="User Name", color="Mapping Name", title="Resource creation duration")

        fig.update_layout(xaxis_title="Resource creation duration, in seconds")
        fig.update_layout(yaxis_title="User index")
        fig.update_yaxes(autorange="reversed") # otherwise users are listed from the bottom up
        fig.update_xaxes(range=[0, df["Duration"].max()*1.1])

        title = f"Duration of the KServe Resource Creation"

        fig.update_layout(title=title, title_x=0.5,)

        return fig, ""
