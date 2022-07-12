from collections import defaultdict

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import timeline_data

def register():
    ExecutionDistribution("Execution time distribution")

class ExecutionDistribution():
    def __init__(self, name):
        self.name = name
        self.id_name = name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        cnt = sum(1 for _ in common.Matrix.all_records(settings, setting_lists))
        if cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {cnt}."

        data_timeline = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            break

        steps = []
        data = []
        for test_pod, ods_ci_output in entry.results.ods_ci_output.items():
            user_idx = test_pod.split("-")[2]
            for step_name, test_times in ods_ci_output.items():
                if step_name not in steps:
                    steps.append(step_name)

                if test_times.status != "PASS":
                    continue

                step_index = steps.index(step_name)

                data.append(dict(user=1, step_name=step_name,
                                 timelength=(test_times.finish - test_times.start).total_seconds()))


        df = pd.DataFrame(data)
        fig = px.histogram(df, x="timelength",
                           y="user", color="step_name",
                           marginal="violin",
                           barmode="overlay",
                           histnorm='probability density',
                           hover_data=df.columns)
        fig.update_layout(xaxis_title="Step timelength (in seconds)")

        user_count = entry.settings.user_count

        fig.update_layout(title=f"Execution time distribution with {user_count} users", title_x=0.5)

        return fig, ""
