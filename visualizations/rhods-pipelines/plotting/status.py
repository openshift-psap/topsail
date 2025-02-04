from collections import defaultdict

import statistics as stats

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

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

        cnt = common.Matrix.count_records(settings, setting_lists)
        if cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            break

        cfg__show_only_step = cfg.get("step", False)
        cfg__time_to_reach_step = cfg.get("time_to_reach_step", False)
        cfg__only_prefix = cfg.get("only_prefix", [])
        cfg__remove_prefix = cfg.get("remove_prefix", True)

        data = []

        if cfg__show_only_step or cfg__time_to_reach_step:
            times_data = []

        if cfg__time_to_reach_step:
            accumulated_timelength = 0
            last_user_idx = 0

        previous_step_time = entry.results.tester_job.creation_time
        for user_idx, user_data in entry.results.user_data.items():
            for step_idx, (step_name, step_time) in enumerate(user_data.progress.items()):

                if cfg__time_to_reach_step and user_idx != last_user_idx:
                    accumulated_timelength = 0
                    last_user_idx = user_idx

                if cfg__show_only_step and step_name != cfg__show_only_step:
                    continue

                timelength = (step_time - previous_step_time).total_seconds()
                previous_step_time = step_time

                if cfg__only_prefix:
                    keep = False
                    for prefix in cfg__only_prefix:
                        if step_name.startswith(prefix):
                            keep = True
                    if not keep:
                        continue

                if cfg__time_to_reach_step:
                    accumulated_timelength += timelength
                    if step_name != cfg__time_to_reach_step:
                        continue

                    timelength = accumulated_timelength
                    step_name = f"Time to reach {step_name}"

                data.append(dict(user=1,
                                 step_name=step_name if not cfg__remove_prefix else step_name.partition(".")[-1],
                                 timelength=timelength))

                if cfg__show_only_step or cfg__time_to_reach_step:
                    times_data.append(data[-1]["timelength"])

        if not data:
            return None, "No data to plot ..."

        df = pd.DataFrame(data)
        fig = px.histogram(df, x="timelength",
                           y="user", color="step_name",
                           marginal="box",
                           barmode="overlay",
                           hover_data=df.columns)
        fig.update_layout(xaxis_title="Step timelength (in seconds)")

        user_count = entry.results.user_count

        title = f"Execution time distribution with {user_count} users"
        if cfg__show_only_step:
            step_name = cfg__show_only_step if not cfg__remove_prefix else cfg__show_only_step.partition(".")[-1]
            title += f"<br><b>{step_name}</b>"
            fig.layout.update(showlegend=False)
        elif cfg__time_to_reach_step:
            title += f"<br><b>Time to reach {cfg__time_to_reach_step}</b>"
            fig.layout.update(showlegend=False)

        fig.update_layout(title=title, title_x=0.5)

        msg = []
        if (cfg__show_only_step or cfg__time_to_reach_step) and len(times_data) >= 2:
            q1, med, q3 = stats.quantiles(times_data)
            q90 = stats.quantiles(times_data, n=10)[8] # 90th percentile
            q100 = max(times_data)

            def time(sec):
                if sec <= 120:
                    return f"{sec:.0f} seconds"
                else:
                    return f"{sec/60:.1f} minutes"

            msg.append(f"25% of the users got their notebook in less than {time(q1)} [Q1]")
            msg.append(html.Br())
            msg.append(f"50% of the users got their notebook in less than {time(med)} (+ {time(med-q1)}) [median]")
            msg.append(html.Br())
            msg.append(f"75% of the users got their notebook in less than {time(q3)} (+ {time(q3-med)}) [Q3]")
            msg.append(html.Br())
            msg.append(f"90% of the users got their notebook in less than {time(q90)} (+ {time(q90-q3)}) [90th quantile]")
            msg.append(html.Br())
            msg.append(f"There are {time(q3 - q1)} between Q1 and Q3.")
            msg.append(html.Br())
            msg.append(f"There are {time(q100 - q3)} between Q3 and Q4.")
            msg.append(html.Br())

        return fig, msg
