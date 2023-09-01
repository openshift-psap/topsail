from collections import defaultdict
import datetime

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    UserProgress()

def get_data_UserProgress(results):
    data = []

    for user_idx, user_data in results.user_data.items():
        if not user_data: continue

        previous_step_time = results.test_start_end_time.start

        for key, step_time in user_data.progress.items():
            timelength = (step_time - previous_step_time).total_seconds()
            previous_step_time = step_time

            entry_data = {}
            data.append(entry_data)

            entry_data["User Name"] = f"User #{user_idx}"
            entry_data["User Index"] = user_idx
            entry_data["Step Name"] = key
            entry_data["Time"] = step_time
            entry_data["Step Duration"] = timelength

    return data


class UserProgress():
    def __init__(self):
        self.name = "User progress"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        expe_cnt = common.Matrix.count_records(settings, setting_lists)
        if expe_cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {expe_cnt}."

        cfg__hide_launch_delay = cfg.get("hide_launch_delay", True)

        for entry in common.Matrix.all_records(settings, setting_lists):
            pass # entry is set

        data = get_data_UserProgress(entry.results)
        df = pd.DataFrame(data).sort_values(by=["User Index", "Step Name"], ascending=True)

        fig = px.area(df, y="User Name", x="Step Duration", color="Step Name")
        fig.update_layout(xaxis_title="Timeline (in seconds)")
        fig.update_layout(yaxis_title="")
        fig.update_yaxes(autorange="reversed") # otherwise users are listed from the bottom up

        if cfg__hide_launch_delay:
            fig.for_each_trace(lambda trace: trace.update(visible="legendonly")
                               if "launch_delay" in trace.name or "statesignal" in trace.name else ())
        return fig, ""
