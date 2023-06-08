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

        cnt = common.Matrix.count_records(settings, setting_lists)
        if cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            break


        only_one_user = entry.results.user_count == 1

        cfg__show_all_in_one = cfg.get("all_in_one", False)
        # (long forms for readability)
        cfg__show_user_details = cfg.get("user_details", True if only_one_user else False)
        cfg__stacked = cfg.get("stacked", True if only_one_user else False)

        data = []
        if cfg__show_all_in_one or cfg__show_user_details:
            times_data = []

        for user_idx, ods_ci in entry.results.ods_ci.items() if entry.results.ods_ci else []:
            if not hasattr(ods_ci, "notebook_benchmark"): continue
            if not ods_ci.notebook_benchmark: continue

            measures = ods_ci.notebook_benchmark["measures"]

            user_name = "All the users" if cfg__show_all_in_one else f"User #{user_idx}"

            for measure_idx, measure in enumerate(measures):
                data.append(dict(user=1, user_name=user_name + (f"/{measure_idx}" if cfg__show_user_details else ""),
                                 measure=measure))

                if cfg__show_all_in_one or cfg__show_user_details:
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

        if cfg__stacked:
            fig.update_layout(barmode='stack')

        msg = []
        if cfg__show_all_in_one or cfg__show_user_details:
            q0 = min(times_data)
            q100 = max(times_data)
            q1, med, q3 = stats.quantiles(times_data)
            q90 = stats.quantiles(times_data, n=10)[8] # 90th percentile

            msg.append(f"25% of the measurements ran in less than {q1:.2f} seconds [Q1]")
            msg.append(html.Br())
            msg.append(f"50% of the measurements ran in less than {med:.2f} seconds (+ {med-q1:.2f}s) [median]")
            msg.append(html.Br())
            msg.append(f"75% of the measurements ran in less than {q3:.2f} seconds (+ {q3-med:.2f}s) [Q3]")
            msg.append(html.Br())
            msg.append(f"90% of the measurements ran less than {q90:.2f} seconds (+ {q90-q3:.2f}s) [90th quantile]")
            msg.append(html.Br())
            msg.append(f"There are {len(times_data)} measurements.")
            msg.append(html.Br())
            msg.append(f"The median measurement time is {med:.2f} seconds.")
            msg.append(html.Br())
            q3_q1 = q3 - q1
            msg.append(f"There are {q3_q1:.2f} seconds between Q1 and Q3 ({q3_q1/med*100:.1f}% of the median).")
            msg.append(html.Br())
            q100_q0 = q100 - q0
            msg.append(f"There are {q100 - q0:.2f} seconds between min and max ({q100_q0/med*100:.1f}% of the median).")
            msg.append(html.Br())
            try:
                if "instance_type" in entry.settings.__dict__:
                    machine_type = entry.settings.instance_type
                elif not entry.results.rhods_cluster_info.compute:
                    machine_type = "not available (no compute node?)"
                else:
                    machine_type = entry.results.rhods_cluster_info.compute[0].instance_type
            except Exception as e:
                machine_type = f"not available ({e})"

            msg += ["The notebook machine instance type is ", html.Code(machine_type)]
            msg.append(html.Br())

            if entry.results.notebook_perf:
                res = entry.results.notebook_perf.notebook["spec"]["template"]["spec"]["containers"][0]["resources"]
                rq = f"mem={res['requests']['memory']} and cpu={res['requests']['cpu']}"
                lt = f"mem={res['limits']['memory']} and cpu={res['limits']['cpu']}"
                msg.append(f"The notebook requested {rq}, limited to {lt}.")
            msg.append(html.Br())

        return fig, msg
