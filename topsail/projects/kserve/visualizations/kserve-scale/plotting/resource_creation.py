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
                "Resource": f"Model {pod_time.model_id:03d} | Pod",
                "Create Time": pod_time.creation_time,
                "Kind": "Pod",
                "User Name": f"User #{pod_time.user_idx:03}",
                "User Index": pod_time.user_idx,
            })

        for user_idx, user_data in entry.results.user_data.items():
            if not user_data.resource_times: continue

            for resource_name, resource_times in user_data.resource_times.items():
                data.append({
                    "Namespace" : resource_times.namespace,
                    "Resource": f"Model {resource_times.model_id:03d} | {resource_times.kind}",
                    "Create Time": resource_times.creation,
                    "Kind": resource_times.kind,
                    "User Name": f"User #{user_idx:03}",
                    "User Index": user_idx,
                })

        if not data:
            return None, "No data available"

        df = pd.DataFrame(data).sort_values(by=["User Index", "Resource"], ascending=True)

        fig = px.line(df, x="Create Time", y="User Name", title="Resource creation time", color="Resource")

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
        cfg__as_distribution = cfg.get("as_distribution", False)

        for entry in common.Matrix.all_records(settings, setting_lists):
            pass # entry is set

        models_per_ns = entry.results.test_config.get("tests.scale.model.replicas")
        isvc_basename = entry.results.test_config.get("tests.scale.model.name")
        serving_runtime_name = entry.results.test_config.get("tests.scale.model.name")
        mapping = dict()

        for model_id in range(models_per_ns):
            if cfg__model_id is not None and cfg__model_id != model_id: continue

            isvc_name = f"model_{model_id}"
            mapping[f"InferenceService/{isvc_name}"] = [
                f"Service/{isvc_name}",
            ]

        data = []
        for user_idx, user_data in entry.results.user_data.items():
            for base_name, dependencies in mapping.items():
                try: base_time = user_data.resource_times[base_name].creation
                except KeyError: continue
                except TypeError: continue

                for dep_name in dependencies:
                    try: dep_time = user_data.resource_times[dep_name].creation
                    except KeyError: continue
                    except TypeError: continue

                    duration = (dep_time - base_time).total_seconds()
                    model_id = user_data.resource_times[dep_name].model_id
                    data.append({
                        "Base Time": base_time,
                        "Mapping Name": f"Model {-1 if model_id is None else model_id:03d} | {base_name.split('/')[0]} -> {dep_name.split('/')[0]}",
                        "Model": f"Model {model_id:03d}",
                        "Duration": duration,
                        "User Index": user_idx,
                        "User Name": f"User #{user_idx:03d}",
                    })

        if not data:
            return None, "No data available"



        if cfg__as_distribution:
            df = pd.DataFrame(data).sort_values(by=["Model"], ascending=True)

            fig = px.histogram(df, x="Model", y="Duration", color="User Name",
                               barmode="overlay",
                               title="Resource creation duration distribution")
        else:
            df = pd.DataFrame(data).sort_values(by=["User Name", "Model"], ascending=True)

            fig = px.line(df, x="Duration", y="User Name", color="Mapping Name", title="Resource creation duration")
            fig.update_yaxes(autorange="reversed") # otherwise users are listed from the bottom up

            fig.update_layout(xaxis_title="Resource creation duration, in seconds")
            fig.update_layout(yaxis_title="User index")
            fig.update_xaxes(range=[0, df["Duration"].max()*1.1])

        title = f"Duration of the KServe Resource Creation"

        fig.update_layout(title=title, title_x=0.5,)

        return fig, ""
