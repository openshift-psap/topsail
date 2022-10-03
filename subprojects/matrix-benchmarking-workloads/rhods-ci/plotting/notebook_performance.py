from collections import defaultdict

import statistics as stats

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    NotebookPerformance("Notebook Performance")

class NotebookPerformance():
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

        for entry in common.Matrix.all_records(settings, setting_lists):
            break


        cfg__show_all_in_one = cfg.get("all_in_one", False)

        data = []
        if cfg__show_all_in_one:
            times_data = []

        for user_idx, ods_ci_notebook_benchmark in entry.results.ods_ci_notebook_benchmark.items():
            if not ods_ci_notebook_benchmark: continue

            measures = ods_ci_notebook_benchmark["measures"]

            user_name = "All the users" if cfg__show_all_in_one else f"User #{user_idx}"

            for measure in ods_ci_notebook_benchmark["measures"]:
                data.append(dict(user=1, user_name=user_name, measure=measure))

                if cfg__show_all_in_one:
                    times_data.append(measure)

        if not data:
            return None, "No data to plot ..."

        df = pd.DataFrame(data)
        fig = px.histogram(df, x="measure",
                           y="user", color="user_name",
                           marginal="box",
                           barmode="overlay",
                           hover_data=df.columns)
        fig.update_layout(xaxis_title="Benchmark time (in seconds)")

        user_count = entry.settings.user_count

        title = f"Notebook Performance distribution with {user_count} users"

        if cfg__show_all_in_one:
            title += f"<br><b>All the users</b>"
            fig.layout.update(showlegend=False)

        fig.update_layout(title=title, title_x=0.5)

        msg = []
        if cfg__show_all_in_one:
            q1, med, q3 = stats.quantiles(times_data)
            q90 = stats.quantiles(times_data, n=10)[8] # 90th percentile

            msg.append(f"25% of the users got their notebook in less than {q1/60:.1f} minutes [Q1]")
            msg.append(html.Br())
            msg.append(f"50% of the users got their notebook in less than {med/60:.1f} minutes (+ {med-q1:.0f}s) [median]")
            msg.append(html.Br())
            msg.append(f"75% of the users got their notebook in less than {q3/60:.1f} minutes (+ {q3-med:.0f}s) [Q3]")
            msg.append(html.Br())
            msg.append(f"90% of the users got their notebook in less than {q90/60:.1f} minutes (+ {q90-q3:.0f}s) [90th quantile]")
            msg.append(html.Br())
            msg.append(f"There are {q3 - q1:.0f} seconds between Q1 and Q3.")
            msg.append(html.Br())

        return fig, msg
