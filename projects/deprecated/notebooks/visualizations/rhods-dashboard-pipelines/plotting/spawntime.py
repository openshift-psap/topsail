from collections import defaultdict
import datetime

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    SpawnTime("Notebook spawn time")
    NotebookResourceCreationTimeline("Notebook Resource Creation Timeline")
    NotebookResourceCreationDelay("Notebook Resource Creation Delay")

def add_ods_ci_progress(entry, hide_failed_users):
    data = []
    for user_idx, ods_ci in entry.results.ods_ci.items():
        if not ods_ci: continue

        failures = ods_ci.exit_code
        if failures and hide_failed_users: continue

        previous_checkpoint_time = entry.results.tester_job.creation_time

        if not ods_ci.progress: continue
        for checkpoint_idx, (checkpoint_name, checkpoint_time) in enumerate(ods_ci.progress.items()):
            if checkpoint_name == "test_execution": continue

            timelength = (checkpoint_time - previous_checkpoint_time).total_seconds()

            entry_data = {}

            entry_data["Step Name"] = checkpoint_name
            entry_data["Step Duration"] = timelength
            entry_data["Step Index"] = checkpoint_idx

            entry_data["User Index"] = user_idx
            entry_data["User Name"] = f"User #{user_idx}"
            if failures:
                entry_data["User Name"] = f"<b>{entry_data['User Name']}</b>"

            data.insert(0, entry_data)

            previous_checkpoint_time = checkpoint_time
    return data


def add_ods_ci_output(entry, keep_failed_steps, hide_failed_users, hide):
    data = []
    def add_substep_time(entry_data, substep_index, name, start, finish):
        subentry_data = entry_data.copy()
        subentry_data["Step Name"] = f"{entry_data['step_index']}.{substep_index} {name}"
        subentry_data["Step Duration"] = (finish - start).total_seconds()
        subentry_data["Step Index"] = entry_data["Step Index"] + substep_index

        return subentry_data

    for user_idx, ods_ci in entry.results.ods_ci.items():
        if not ods_ci: continue

        for step_idx, (step_name, step_status) in enumerate(ods_ci.output.items()):

            failures = ods_ci.exit_code
            if failures and hide_failed_users:
                continue

            step_start = step_status.start
            step_finish = step_status.finish

            if isinstance(hide, int):
                if hide == user_idx:
                    continue

            elif isinstance(hide, str):
                skip = False
                for hide_idx in hide.split(","):
                    if int(hide_idx) == user_idx:
                        skip = True
                        break
                if skip: continue

            entry_data = {}
            entry_data["step_index"] = step_idx
            entry_data["Step Index"] = 100 + step_idx * 10
            entry_data["User Index"] = user_idx
            entry_data["User Name"] = f"User #{user_idx}"
            if failures:
                entry_data["User Name"] = f"<b>{entry_data['User Name']}</b>"

            if step_name in ("Wait for the Notebook Spawn", "Create and Start the Workbench") :
                notebook_pod_times = entry.results.notebook_pod_times[user_idx]

                if not hasattr(notebook_pod_times, "pod_scheduled"): continue
                data.append(add_substep_time(entry_data, 1, "K8s Resources initialization",
                                             step_start, notebook_pod_times.pod_scheduled,))

                if not hasattr(notebook_pod_times, "containers_ready"): continue
                data.append(add_substep_time(entry_data, 2, "Container initialization",
                                             notebook_pod_times.pod_initialized, notebook_pod_times.containers_ready))

                data.append(add_substep_time(entry_data, 3, "User notification",
                                             notebook_pod_times.containers_ready, step_finish))
                continue

            entry_data["Step Name"] = f"{step_idx} - {step_name}"
            entry_data["Step Duration"] = (step_finish - step_start).total_seconds() \
                if keep_failed_steps or step_status.status == "PASS" \
                   else 0

            data.append(entry_data)
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

        if entry.results.ods_ci:
            data += add_ods_ci_progress(entry, hide_failed_users)
            data += add_ods_ci_output(entry, keep_failed_steps, hide_failed_users, hide)

        if not data:
            return None, "No data available"

        df = pd.DataFrame(data).sort_values(by=["User Index", "Step Index"], ascending=True)

        fig = px.area(df, y="User Name", x="Step Duration", color="Step Name")
        fig.update_layout(xaxis_title="Timeline (in seconds)")
        fig.update_layout(yaxis_title="")
        fig.update_yaxes(autorange="reversed") # otherwise users are listed from the bottom up

        if hide_launch_delay:
            fig.for_each_trace(lambda trace: trace.update(visible="legendonly")
                               if not trace.name[0].isdigit() else ())

        title = "Execution Time of the User Steps"
        if keep_failed_steps:
            title += " with the failed steps"
        if hide_failed_users:
            title += " without the failed users"
        if hide_launch_delay:
            title += " without the launch delay"
        fig.update_layout(title=title, title_x=0.5,)

        return fig, ""


class NotebookResourceCreationTimeline():
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

        for resource_name, user_resource_times in entry.results.all_resource_times.items():
            if not user_resource_times: continue

            for user_idx, resource_time in user_resource_times.items():
                data.append({
                        "User Index": user_idx,
                        "User Name": f"User #{user_idx:04d}",
                        "Resource": resource_name,
                        "Create Time": resource_time,
                    })

        if not data:
            return None, "No data available"

        df = pd.DataFrame(data).sort_values(by=["User Index", "Resource"], ascending=True)

        fig = px.line(df, x="Create Time", y="User Name", color="Resource", title="Resource creation time")

        fig.update_layout(xaxis_title="Timeline (in seconds)")
        fig.update_layout(yaxis_title="")
        fig.update_yaxes(autorange="reversed") # otherwise users are listed from the bottom up

        title = "Resources Creation Timeline"

        fig.update_layout(title=title, title_x=0.5,)

        return fig, ""

class NotebookResourceCreationDelay():
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

        mapping = {
            "Namespace/username": {"Secret": ["builder-dockercfg", "builder-token", "default-dockercfg", "default-token", "deployer-dockercfg", "deployer-token", "model-serving-proxy-tls", "modelmesh-serving"],
                                    "Notebook": ["username"]},
            "Notebook/username": {"Route": ["username"],
                                  "StatefulSet": ["username"],
                                  "Service": ["username", "username-tls"],
                                  "Secret": ["username-tls", "username-dockercfg", "username-oauth-config", "username-token"],
                                  "Pod": ["username"]},
            "StatefulSet/username": {"Pod": ["username"]},
        }

        data = []

        for base, dependencies in mapping.items():
            try:
                base_times = entry.results.all_resource_times[base]
            except KeyError: continue

            for user_idx in range(entry.results.user_count):
                try: base_time = base_times[user_idx]
                except KeyError: continue

                for dep_kind, dep_names in dependencies.items():
                    for dep_name in dep_names:
                        try: dep_time = entry.results.all_resource_times[f"{dep_kind}/{dep_name}"][user_idx]
                        except KeyError: continue
                        duration = (dep_time - base_time).total_seconds()

                        data.append({
                            "Base": base,
                            "Name": f"{base} -> {dep_kind}/{dep_name}",
                            "Duration": duration,
                            "User Index": user_idx,
                            "User Name": f"User #{user_idx:04d}",
                        })


        if not data:
            return None, "No data available"

        df = pd.DataFrame(data).sort_values(by=["User Index", "Base"], ascending=True)

        fig = px.line(df, x="Duration", y="User Name", color="Name", title="Resource creation duration")

        fig.update_layout(xaxis_title="Resource creation duration, in seconds")
        fig.update_layout(yaxis_title="User index")
        fig.update_yaxes(autorange="reversed") # otherwise users are listed from the bottom up

        title = "Duration of the Notebook Resource Creation"

        fig.update_layout(title=title, title_x=0.5,)

        return fig, ""
