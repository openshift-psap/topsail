from collections import defaultdict
import logging

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from ..store import utils


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

        entry_names = set()
        data = []

        for entry in common.Matrix.all_records(settings, setting_lists):
            entry_name = entry.get_name(variables)
            entry_names.add(entry_name)

            sort_index = entry.get_settings()[ordered_vars[0]] if len(variables) == 1 \
                else entry_name

            accumulated_timelength = 0
            current_index = -1
            for user_idx, step_name, step_status, step_time, _not_used_step_start_time in utils.parse_users(entry):
                if current_index != user_idx:
                    accumulated_timelength = 0
                    current_index = user_idx

                if step_status != "PASS":
                    continue

                accumulated_timelength += step_time
                if step_name != cfg__time_to_reach_step:
                    continue

                data.append(dict(Version=entry_name,
                                SortIndex=sort_index,
                                Time=accumulated_timelength))

        if not data:
            return None, "No data found :/"

        df = pd.DataFrame(data).sort_values(by=["SortIndex"])

        fig = px.box(df, x="Version", y="Time", color="Version")

        msg.append(html.H4("Median launch time"))
        for entry_name in sorted(entry_names):
            res = df[df["Version"] == entry_name]
            if res.empty:
                msg.append(html.Ul(html.Li(html.B(f"{entry_name}: no data ..."))))
                continue
            value_50 = res["Time"].quantile(0.50)
            msg.append(html.Ul(html.Li([html.B(f"{entry_name}:") if entry_name else "", f" {value_50:.0f} seconds"])))

        fig.update_layout(title=f"Time to launch the notebooks", title_x=0.5,)
        fig.update_layout(yaxis_title="Launch time")
        fig.update_layout(xaxis_title="")

        return fig, msg
