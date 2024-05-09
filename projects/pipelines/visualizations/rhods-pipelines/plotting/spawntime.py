from collections import defaultdict
import datetime
import statistics as stats
import re

from dash import html
import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    SpawnTime("User Execution Time")
    RunTimeDistribution("Median runtime timeline")
    ResourceCreationTimeline()
    ResourceCreationDelay()
    RunCreationDelay()

def add_progress(entry, hide_failed_users, only_prefix=[], remove_prefix=True):
    data = []
    for user_idx, user_data in entry.results.user_data.items():
        if not user_data: continue

        failures = user_data.exit_code
        if failures and hide_failed_users: continue

        previous_step_time = entry.results.tester_job.creation_time

        if not user_data.progress: continue

        for step_idx, (step_name, step_time) in enumerate(user_data.progress.items()):
            timelength = (step_time - previous_step_time).total_seconds()
            previous_step_time = step_time

            if only_prefix:
                keep = False
                for prefix in only_prefix:
                    if step_name.startswith(prefix):
                        keep = True
                if not keep: continue


            entry_data = {}

            entry_data["Step Name"] = step_name if not remove_prefix else step_name.partition(".")[-1]
            entry_data["Step Duration"] = timelength
            entry_data["Step Index"] = step_idx

            entry_data["User Index"] = user_idx
            entry_data["User Name"] = f"User #{user_idx}"
            if failures:
                entry_data["User Name"] = f"<b>{entry_data['User Name']}</b>"

            data.insert(0, entry_data)

    return data


class SpawnTime():
    def __init__(self, name):
        self.name = name
        self.id_name = name

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

        hide_launch_delay = cfg.get("hide_launch_delay", False)
        keep_failed_steps = cfg.get("keep_failed_steps", False)
        hide_failed_users = cfg.get("hide_failed_users", False)
        hide = cfg.get("hide", None)

        data += add_progress(entry, hide_failed_users)

        if not data:
            return None, "No data available"

        df = pd.DataFrame(data).sort_values(by=["User Index", "Step Index"], ascending=True)

        fig = px.area(df, y="User Name", x="Step Duration", color="Step Name")
        fig.update_layout(xaxis_title="Timeline (in seconds)")
        fig.update_layout(yaxis_title="")
        fig.update_yaxes(autorange="reversed") # otherwise users are listed from the bottom up

        if hide_launch_delay:
            fig.for_each_trace(lambda trace: trace.update(visible="legendonly")
                               if "launch_delay" in trace.name or "statesignal" in trace.name else ())

        title = "Execution Time of the User Steps"
        if keep_failed_steps:
            title += " with the failed steps"
        if hide_failed_users:
            title += " without the failed users"
        if hide_launch_delay:
            title += " without the launch delay"
        fig.update_layout(title=title, title_x=0.5,)

        return fig, ""

class RunTimeDistribution():
    def __init__(self, name, show_successes=False):
        self.name = name
        self.id_name = name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        user_counts = set()

        if not common.Matrix.has_records(settings, setting_lists):
            return None, "No experiments to plot"

        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            results = entry.results
            entry_name = ", ".join([f"{key}={entry.settings.__dict__[key]}" for key in variables])

            user_counts.add(results.user_count)

            previous_step_time = entry.results.tester_job.creation_time
            for user_index, user_data in entry.results.user_data.items():
                if user_data.exit_code != 0:
                    continue

                for step_name, step_time in user_data.progress.items():

                    data.append(dict(
                        UserCount=results.user_count,
                        Step=step_name + entry_name,
                        Time=(step_time - previous_step_time).total_seconds(),
                    ))
                    previous_step_time = step_time

        data = add_progress(entry, hide_failed_users=True, only_prefix=["ansible"], remove_prefix=True)

        if not data:
            return None, "No data to plot ..."

        data_df = pd.DataFrame(data)
        data_df = data_df.sort_values(by=["Step Name"])

        stats_data = []
        base_value = 0
        steps = data_df["Step Name"].unique()
        notebook_ready_time = None
        msg = []
        for step_name in steps:
            step_df = data_df[data_df["Step Name"] == step_name]
            q1, median, q3 = stats.quantiles(step_df["Step Duration"]) if len(step_df["Step Duration"]) > 1 else (step_df["Step Duration"].iloc[0], step_df["Step Duration"].iloc[0], step_df["Step Duration"].iloc[0])
            q1_dist = median-q1
            q3_dist = q3-median
            stats_data.append(dict(
                Steps=step_name,
                MedianDuration=median,
                Q1=q1_dist,
                Q3=q3_dist,
                UserCount=str(entry.results.user_count),
                Base=base_value,
            ))

            q1_txt = f"-{q1_dist:.0f}s" if round(q1_dist) >= 2 else ""
            q3_txt = f"+{q3_dist:.0f}s" if round(q3_dist) >= 2 else ""
            msg += [f"{step_name}: {median:.0f}s {q1_txt}{q3_txt}", html.Br()]

            base_value += median
            if step_name.endswith("Go to JupyterLab Page"):
                notebook_ready_time = base_value
                msg += ["---", html.Br()]

        stats_df = pd.DataFrame(stats_data)

        fig = px.bar(stats_df,
                     x="MedianDuration", y="Steps", color="Steps", base="Base",
                     error_x_minus="Q1", error_x="Q3",
                     title="Median runtime timeline")

        if notebook_ready_time:
            fig.add_scatter(name="Time to reach JupyterLab",
                            x=[notebook_ready_time, notebook_ready_time],
                            y=[steps[0], steps[-1]])
        fig.update_layout(xaxis_title="Timeline (in seconds). Error bars show Q1 and Q3.")
        fig.update_layout(yaxis_title="", title_x=0.5,)

        return fig, msg

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

        cfg__dspa_only = cfg.get("dspa_only", False)
        cfg__pipeline_task_only = cfg.get("pipeline_task_only", False)
        skip_pods = True

        workflow_mapping = {}
        workflow_ordering = {}
        data = []
        # Assemble the workflow names
        for user_idx, user_data in entry.results.user_data.items():
            for resource_name, creation_time in user_data.resource_times.items():
                resource_type, resource_id = resource_name.split("/")
                if resource_type == "Workflow":
                    workflow_mapping[resource_id] = user_idx
                    if user_idx not in workflow_ordering:
                        workflow_ordering[user_idx] = []
                    workflow_ordering[user_idx].append({"name": resource_name, "creation_time": creation_time})
                    workflow_ordering[user_idx] = sorted(workflow_ordering[user_idx], key=lambda x: x["creation_time"])
        for user_idx, user_data in entry.results.user_data.items():
            for resource_name, creation_time in user_data.resource_times.items():
                resource_key = re.sub(r'n([0-9]+)-', "nX-", resource_name)
                if resource_name.split("/")[0] == "Workflow":
                    workflow_run_name = user_data.workflow_run_names[resource_name.split("/")[1]]
                    resource_key = f"Workflow/{workflow_run_name}"
                resource_key = resource_key.replace(f"user{user_idx}-", "")
                data.append({
                        "User Index": int(user_idx),
                        "User Name": f"User #{user_idx:03d}",
                        "Resource": resource_name,
                        "Resource Type": resource_key,
                        "Create Time": creation_time,
                    })
        if not skip_pods:
            for user_idx, user_data in entry.results.user_data.items():
                for pod_time in user_data.pod_times:
                    if pod_time.parent_workflow != "" and pod_time.parent_workflow in workflow_mapping and workflow_mapping[pod_time.parent_workflow] != user_idx:
                        continue
                    resource_name = f"Pod/{pod_time.pod_friendly_name}"
                    resource_key = resource_name.replace(f"user{user_idx}", "userX")
                    resource_key = re.sub(r'n([0-9]+)-', "nX-", resource_key)
                    data.append({
                            "User Index": int(user_idx),
                            "User Name": f"User #{user_idx:03d}",
                            "Resource": f"Pod/{pod_time.pod_friendly_name}",
                            "Resource Type": resource_key,
                            "Create Time": pod_time.creation_time,
                        })
        if not data:
            return None, "No data available"

        df = pd.DataFrame(data).sort_values(by=["User Index", "Resource"], ascending=True)

        fig = px.line(
            df,
            x="Create Time",
            y="User Name",
            color="Resource Type",
            title="Resource creation time",
            markers=True,
            category_orders={
                "User Name": df["User Name"].drop_duplicates().tolist()
            }
        )

        fig.update_layout(xaxis_title="Timeline (in seconds)")
        fig.update_layout(yaxis_title="")

        what = ""
        if cfg__dspa_only:
            what = "DSPApplication "
        if cfg__pipeline_task_only:
            what = "Pipelines "

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

        data = []
        for user_idx, user_data in entry.results.user_data.items():
            ns_idx = -1
            for resource_name, creation_time in user_data.resource_times.items():
                temp_ns = re.search(r'n([0-9]+)-', resource_name)
                if temp_ns:
                    ns_idx = int(temp_ns.groups()[0])
                    break
            mapping = {
                f"DataSciencePipelinesApplication/n{ns_idx}-sample": {
                    "Deployment": [
                        f"ds-pipeline-persistenceagent-n{ns_idx}-sample",
                        f"ds-pipeline-n{ns_idx}-sample",
                        f"ds-pipeline-scheduledworkflow-n{ns_idx}-sample",
                        f"ds-pipeline-workflow-controller-n{ns_idx}-sample",
                        f"ds-pipeline-ui-n{ns_idx}-sample",
                        f"mariadb-n{ns_idx}-sample",
                    ],
                },
            }
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

                        mapping_name = f"{base_name} -> {dep_kind}/{dep_name}"
                        mapping_key = re.sub(r'n([0-9]+)-', "nX-", mapping_name)
                        data.append({
                            "Base": base_name,
                            "Mapping Name": mapping_name,
                            "Mapping Key": mapping_key,
                            "Duration": duration,
                            "Namespace Index": ns_idx,
                            "Namespace Name": f"Project #{ns_idx:03d}",
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

                    mapping_name = f"{base_name} -> {dep_kind}/{dep_name}"
                    mapping_key = re.sub(r'n([0-9]+)-', "nX-", mapping_name)
                    data.append({
                        "Base": base_name,
                        "Mapping Name": mapping_name,
                        "Mapping Key": mapping_key,
                        "Duration": duration,
                        "Namespace Index": ns_idx,
                        "Namespace Name": f"Project #{ns_idx:03d}",
                    })

        if not data:
            return None, "No data available"

        df = pd.DataFrame(data).sort_values(by=["Namespace Index", "Base"], ascending=True)

        fig = px.line(df, x="Duration", y="Namespace Name", color="Mapping Key", title="Resource creation duration", markers=True)

        fig.update_layout(xaxis_title="Resource creation duration, in seconds")
        fig.update_layout(yaxis_title="Namespace index")
        fig.update_yaxes(autorange="reversed") # otherwise users are listed from the bottom up
        fig.update_xaxes(range=[-1, df["Duration"].max()*1.1])

        what = ""
        if cfg__dspa_only:
            what = "DSPApplication "
        if cfg__pipeline_task_only:
            what = "Pipelines "
        title = f"Duration of the {what}Resource Creation"

        fig.update_layout(title=title, title_x=0.5,)

        return fig, ""

class RunCreationDelay():
    def __init__(self):
        self.name = "Run Creation Delay"
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

        workflow_mapping = {}
        workflow_ordering = {}
        data = []
        # Assemble the workflow names
        for user_idx, user_data in entry.results.user_data.items():
            for resource_name, creation_time in user_data.resource_times.items():
                resource_type, resource_id = resource_name.split("/")
                if resource_type == "Workflow":
                    workflow_mapping[resource_id] = user_idx
                    if user_idx not in workflow_ordering:
                        workflow_ordering[user_idx] = []
                    workflow_ordering[user_idx].append({"name": resource_name, "creation_time": creation_time})
                    workflow_ordering[user_idx] = sorted(workflow_ordering[user_idx], key=lambda x: x["creation_time"])
        for user_idx, user_data in entry.results.user_data.items():
            for resource_name, creation_time in user_data.resource_times.items():
                resource_key = re.sub(r'n([0-9]+)-', "nX-", resource_name)
                if resource_name.split("/")[0] == "Workflow":
                    workflow_run_name = user_data.workflow_run_names[resource_name.split("/")[1]]
                    resource_key = f"Workflow/{workflow_run_name}"
                    resource_key = resource_key.replace(f"user{user_idx}-", "")
                    data.append({
                            "User Index": int(user_idx),
                            "User Name": f"User #{user_idx:03d}",
                            "Resource": resource_name,
                            "Run Name": resource_key,
                            "Delay Time": (user_data.workflow_start_times[resource_name.split("/")[1]] - user_data.submit_run_times[workflow_run_name]).total_seconds(),
                        })
        if not data:
            return None, "No data available"

        data_df = pd.DataFrame(data)
        data_df = data_df.sort_values(by=["Run Name"])

        stats_data = []
        base_value = 0
        run_steps = data_df["Run Name"].unique()
        msg = []

        for run_step in run_steps:
            step_df = data_df[data_df["Run Name"] == run_step]
            q1, median, q3 = stats.quantiles(step_df["Delay Time"]) if len(step_df["Delay Time"]) > 1 else (step_df["Delay Time"].iloc[0], step_df["Delay Time"].iloc[0], step_df["Delay Time"].iloc[0])
            q1_dist = median-q1
            q3_dist = q3-median
            stats_data.append(dict(
                Runs=run_step,
                MedianDuration=median,
                Q1=q1_dist,
                Q3=q3_dist,
                UserCount=str(entry.results.user_count),
            ))

            q1_txt = f"-{q1_dist:.0f}s" if round(q1_dist) >= 2 else ""
            q3_txt = f"+{q3_dist:.0f}s" if round(q3_dist) >= 2 else ""
            msg += [f"{run_step}: {median:.0f}s {q1_txt}{q3_txt}", html.Br()]

        stats_df = pd.DataFrame(stats_data)

        fig = px.bar(stats_df,
                     x="Runs", y="MedianDuration", color="Runs",
                     error_x_minus="Q1", error_x="Q3",
                     title="Median Run Creation Delay")

        fig.update_layout(xaxis_title="Runs in Order of Execution")
        fig.update_layout(yaxis_title="Delay from Submitting to Creation (in seconds)")

        what = ""
        if cfg__dspa_only:
            what = "DSPApplication "
        if cfg__pipeline_task_only:
            what = "Pipelines "

        title = f"{what}Run Creation Delay Distribution"

        fig.update_layout(title=title, title_x=0.5,)

        return fig, msg

