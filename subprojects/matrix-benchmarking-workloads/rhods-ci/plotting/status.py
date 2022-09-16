from collections import defaultdict

import statistics as stats

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

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

        cfg__show_only_step = cfg.get("step", False)

        steps = []
        data = []

        if cfg__show_only_step:
            times_data = []
        for user_idx, ods_ci_output in entry.results.ods_ci_output.items():
            for step_name, test_times in ods_ci_output.items():
                if cfg__show_only_step and step_name != cfg__show_only_step:
                    continue

                if step_name not in steps:
                    steps.append(step_name)

                if test_times.status != "PASS":
                    continue

                step_index = steps.index(step_name)

                data.append(dict(user=1, step_name=step_name,
                                 timelength=(test_times.finish - test_times.start).total_seconds()))
                if cfg__show_only_step:
                    times_data.append(data[-1]["timelength"])

        df = pd.DataFrame(data)
        fig = px.histogram(df, x="timelength",
                           y="user", color="step_name",
                           marginal="violin",
                           barmode="overlay",
                           histnorm='probability density',
                           hover_data=df.columns)
        fig.update_layout(xaxis_title="Step timelength (in seconds)")

        user_count = entry.settings.user_count

        title = f"Execution time distribution with {user_count} users"
        if cfg__show_only_step:
            title += f"<br><b>{cfg__show_only_step}</b>"
            fig.layout.update(showlegend=False)
        fig.update_layout(title=title, title_x=0.5)

        if cfg__show_only_step:
            q1, med, q3 = stats.quantiles(times_data)
            msg = f"Q1 = {q1:.1f}s, median = {med:.1f}s, Q3 = {q3:.1f}s"
        else:
            msg = ""
        return fig, msg
