from collections import defaultdict

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    SpawnTime("Notebook spawn time")

class SpawnTime():
    def __init__(self, name):
        self.name = name
        self.id_name = name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        expe_cnt = sum(1 for _ in common.Matrix.all_records(settings, setting_lists))
        if expe_cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            results = entry.results

        data = []

        keep_failed_steps = cfg.get("keep_failed_steps", False)
        hide_failed_users = cfg.get("hide_failed_users", False)

        for user_id, ods_ci_output in entry.results.ods_ci_output.items():
            first_step = True
            for step_idx, (step_name, step_status) in enumerate(ods_ci_output.items()):

                failures = entry.results.ods_ci_exit_code[user_id]
                if failures and hide_failed_users: continue

                step_start = step_status.start
                step_finish = step_status.finish
                if first_step:
                    first_step = False
                    entry_data = {}

                    entry_data["Step Name"] = "Launch delay and initialization"
                    entry_data["Step Duration"] = (step_start - entry.results.job_creation_time).total_seconds()
                    entry_data["Step Index"] = -1
                    entry_data["User Index"] = user_id
                    entry_data["User Name"] = f"User #{user_id}"
                    if failures:
                        entry_data["User Name"] = f"<b>{entry_data['User Name']}</b>"

                    data.insert(0, entry_data)

                hide = cfg.get("hide", None)
                if isinstance(hide, int):
                    if hide == user_id: continue

                elif isinstance(hide, str):
                    skip = False
                    for hide_idx in hide.split(","):
                        if int(hide_idx) == user_id:
                            skip = True
                    if skip: continue

                entry_data = {}

                if keep_failed_steps or step_status.status == "PASS":
                    entry_data["Step Duration"] = (step_finish - step_start).total_seconds()
                else:
                    entry_data["Step Duration"] = 0

                entry_data["Step Name"] = f"{step_idx} - {step_name}"

                entry_data["User Name"] = f"User #{user_id}"
                if failures:
                    entry_data["User Name"] = f"<b>{entry_data['User Name']}</b>"

                data.append(entry_data)

        if not data:
            return {}, "No data available"

        df = pd.DataFrame(data).sort_values(by=["User Index", "Step Index"], ascending=True)

        fig = px.area(df, y="User Name", x="Step Duration", color="Step Name")
        fig.update_layout(xaxis_title="Timeline (in seconds)")
        fig.update_layout(yaxis_title="")
        fig.update_yaxes(autorange="reversed") # otherwise users are listed from the bottom up

        title = "Execution Time of the User Steps"
        if keep_failed_steps:
            title += " with the failed steps"
        if hide_failed_users:
            title += " without the failed users"

        fig.update_layout(title=title, title_x=0.5,)

        return fig, ""
