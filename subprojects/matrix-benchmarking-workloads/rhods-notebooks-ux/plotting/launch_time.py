from collections import defaultdict

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common


def register():
    LaunchTimeDistribution("Launch time distribution")
    LaunchTimeDistribution("Step successes", show_successes=True)


class LaunchTimeDistribution():
    def __init__(self, name, show_successes=False):
        self.name = name
        self.id_name = name
        self.show_successes = show_successes

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        expe_cnt = sum(1 for _ in common.Matrix.all_records(settings, setting_lists))

        if  expe_cnt != 1:
            return {}, f"ERROR: only one experiment must be selected (found {expe_cnt})"

        for entry in common.Matrix.all_records(settings, setting_lists):
            results = entry.results

        user_count = results.user_count
        data = []
        for pod_name, ods_ci_output in entry.results.ods_ci_output.items():
            for step_name, step_status in ods_ci_output.items():
                if not self.show_successes:
                    if step_status.status != "PASS": continue

                data.append(dict(
                    Event=step_name,
                    Time=step_status.start,
                    Count=1,
                    Status=step_status.status
                ))

        if not data:
            return None, "No data to plot ..."

        df = pd.DataFrame(data)
        if self.show_successes:
            fig = px.histogram(df, x="Event", y="Count", color="Event", pattern_shape="Status")
            fig.update_layout(title=f"Step successes for {user_count} users", title_x=0.5,)
            fig.update_layout(yaxis_title="Number of users")
            fig.update_layout(xaxis_title="")

        else:
            fig = px.box(df[df["Status"] == "PASS"], x="Event", y="Time", color="Event")
            fig.update_layout(title=f"Start time distribution for {user_count} users", title_x=0.5,)
            fig.update_layout(yaxis_title="Launch time")
            fig.update_layout(xaxis_title="")

        msg = []
        for idx, step_name in enumerate(entry.results.ods_ci_output[pod_name]):
            step_times = df[df["Event"] == step_name]["Time"]

            step_start_time = min(df[step_times]["Time"]) if not step_times.empty() \
                else 0

            total_time = (step_times.quantile(1) - step_start_time).total_seconds() / 60 # 100%
            mid_80 = (step_times.quantile(0.90) - step_times.quantile(0.10)).total_seconds() / 60 # 10% <-> 90%
            mid_50 = (step_times.quantile(0.75) - step_times.quantile(0.25)).total_seconds() / 60 # 25% <-> 75%

            msg.append(f"All the users started the step {idx} within {total_time:.1f} minutes, ")
            msg.append(f"80% within {mid_80:.1f} minutes, ")
            msg.append(f"50% within {mid_50:.1f} minutes. ")
            msg.append(html.B(step_name))
            msg.append(html.Br())

        return fig, msg
