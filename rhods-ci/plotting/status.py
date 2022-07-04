from collections import defaultdict

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import timeline_data

def register():
    StatusDistribution("Test status distribution")
    ExecutionDistribution("Execution time distribution")
    ExecutionDistribution("Execution time distribution", show_progress=True)
    ExecutionDistribution("Execution time distribution", with_failed=True)

class ExecutionDistribution():
    def __init__(self, name, show_progress=False, with_failed=False):
        self.show_progress = show_progress
        self.with_failed = with_failed
        if self.with_failed:
            name += " - with_failed"
        if self.show_progress:
            name += " - show_progress"

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

        show_progress = self.show_progress or cfg.get("show_progress", False)
        with_failed = self.with_failed or cfg.get("with_failed", False)

        if show_progress:
            with_failed = True

        steps = []
        data = []
        for test_pod, ods_ci_output in entry.results.ods_ci_output.items():
            if show_progress:
                step_name = "Launch the test"
                steps.append(step_name)
                data.append(dict(user=1, step_name=step_name))

            user_idx = test_pod.split("-")[2]
            for step_name, test_times in ods_ci_output.items():
                if step_name not in steps:
                    steps.append(step_name)
                step_success = test_times.status == "PASS"
                step_index = steps.index(step_name)
                if not with_failed and not step_success:
                    continue

                if show_progress:
                    data.append(dict(user=1 if step_success else 0, step_name=step_name))

                    continue
                else:
                    data.append(dict(user=1, step_name=step_name,
                                     timelength=(test_times.finish - test_times.start).total_seconds()))

                if step_success: continue

                data[-1]["timelength"] = -2 -steps.index(step_name)


        df = pd.DataFrame(data)
        fig = px.histogram(df, x="step_name" if show_progress else "timelength",
                           y="user", color="step_name",
                           marginal=None if show_progress else "violin",
                           barmode="overlay",
                           histnorm=None if show_progress else 'probability density',
                           hover_data=df.columns)
        if show_progress:
            fig.update_layout(xaxis_title="Steps performed")
            fig.update_layout(yaxis_title="Number of users who passed the step")
        else:
            fig.update_layout(xaxis_title="Step timelength (in seconds)")

        user_count = entry.settings.user_count
        if show_progress:
            fig.update_layout(title=f"Execution progress with {user_count} users", title_x=0.5)
        else:
            fig.update_layout(title=f"Execution time distribution with {user_count} users", title_x=0.5)

        return fig, ""

class StatusDistribution():
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

        data = []
        for test_pod, exit_code in entry.results.ods_ci_exit_code.items():
            user_idx = test_pod.split("-")[2]
            user = 1 # f"User {user_idx}"
            data.append(dict(user=user, exit_code=str(exit_code) if exit_code else "0/Success"))

        df = pd.DataFrame(data)

        fig = px.histogram(df, x="exit_code", y="user", color="exit_code",
                           hover_data=df.columns)

        fig.update_layout(yaxis_title="Number of users with the exit code")

        user_count = entry.settings.user_count
        fig.update_layout(title=f"Distribution of the test results of the {user_count} users",
                          title_x=0.5)
        #fig.update_layout(yaxis_title="")

        return fig, ""
