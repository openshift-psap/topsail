from collections import defaultdict

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common


def register():
    MultiNotebookSpawnTime("multi: Notebook Spawn Time")


class MultiNotebookSpawnTime():
    def __init__(self, name):
        self.name = name
        self.id_name = name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        cfg__time_to_reach_step = cfg.get("time_to_reach_step", "Go to JupyterLab Page")

        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            for user_idx, ods_ci_output in entry.results.ods_ci_output.items():
                accumulated_timelength = 0

                for step_name, test_times in ods_ci_output.items():
                    if test_times.status != "PASS":
                        continue

                    timelength = (test_times.finish - test_times.start).total_seconds()

                    accumulated_timelength += timelength
                    if step_name != cfg__time_to_reach_step:
                        continue

                    break

                data.append(dict(Version=entry.location.name,
                                 LaunchTime90Threshold=entry.results.thresholds.get("launch_time_90", None),
                                 LaunchTime75Threshold=entry.results.thresholds.get("launch_time_75", None),
                                 Time=accumulated_timelength))

        if not data:
            return None, "No data found :/"

        df = pd.DataFrame(data).sort_values(by=["Version"])

        fig = px.box(df, x="Version", y="Time", color="Version")

        if 'LaunchTime75Threshold' in df and not df['LaunchTime75Threshold'].isnull().all():
            fig.add_scatter(name="75% launch-time threshold",
                            x=df['Version'], y=df['LaunchTime75Threshold'], mode='lines+markers',
                            marker=dict(color='red', size=15, symbol="triangle-down"),
                            line=dict(color='black', width=3, dash='dot'))

        if 'LaunchTime90Threshold' in df and not df['LaunchTime90Threshold'].isnull().all():
            fig.add_scatter(name="90% launch-time threshold",
                            x=df['Version'], y=df['LaunchTime90Threshold'], mode='lines+markers',
                            marker=dict(color='red', size=15, symbol="triangle-down"),
                            line=dict(color='brown', width=3, dash='dot'))

        fig.update_layout(title=f"Time to launch the notebooks", title_x=0.5,)
        fig.update_layout(yaxis_title="Launch time")
        fig.update_layout(xaxis_title="")

        return fig, ""
