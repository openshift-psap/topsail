import copy
import re
from collections import defaultdict
import os
import base64
import pathlib
import yaml

import statistics as stats

import pandas as pd
from dash import html
from dash import dcc
import plotly.express as px

from matrix_benchmarking.common import Matrix
import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common


def register():
    LoadtimeDistribution()


def generateLoadtimeData(entries, variables):
    data = []

    for entry in entries:

        test_name = entry.get_name(variables)

        for user_data in entry.results.user_data.values():
            for res_name, res_times in user_data.resource_times.items():
                if res_times.kind != "InferenceService":
                    continue

                datum = {}
                datum["test_name"] = test_name
                datum["load_time"] = (res_times.conditions["Ready"] - res_times.creation).total_seconds()
                data.append(datum)

    return data


class LoadtimeDistribution():
    def __init__(self):
        self.name = "Inference Services Load-time Distribution"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        entries = common.Matrix.all_records(settings, setting_lists)
        cnt = common.Matrix.count_records(settings, setting_lists)

        df = pd.DataFrame(generateLoadtimeData(entries, variables))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["test_name"])

        y_key = "load_time"
        if cnt == 1:
            fig = px.histogram(df, x=y_key)

            fig.update_yaxes(title=f"Inference Services Count")
            fig.update_xaxes(title=f"❮ Load time (in seconds)")
        else:
            fig = px.box(df, hover_data=df.columns,
                         x="test_name", y=y_key, color="test_name")
            fig.update_yaxes(range=[0, df[y_key].max() * 1.1])

            fig.update_xaxes(title=f"Test name")
            fig.update_yaxes(title=f"❮ Load time (in seconds)")
        plot_title = f"Distribution of the InferenceServices load time"

        fig.update_layout(title=plot_title, title_x=0.5,)


        msg = []
        for test_name in df.sort_values(by=["test_name"]).test_name.unique():
            stats_data = df[df.test_name == test_name][y_key]

            msg += [html.H3(test_name)]
            q0 = stats_data.min()
            q100 = stats_data.max()
            q1, med, q3 = stats.quantiles(stats_data)
            q90 = stats.quantiles(stats_data, n=10)[8] # 90th percentile

            label = "the InferenceServices were ready in less than"
            unit = "seconds"

            msg.append(f"0% of {label} {q0:.0f} {unit} [min]")
            msg.append(html.Br())
            msg.append(f"25% of {label} {q1:.0f} {unit} [Q1]")
            msg.append(html.Br())
            msg.append(f"50% of {label} {med:.0f} {unit} (+ {med-q1:.0f} {unit}) [median]")
            msg.append(html.Br())
            msg.append(f"75% of {label} {q3:.0f} {unit} (+ {q3-med:.0f} {unit}) [Q3]")
            msg.append(html.Br())
            msg.append(f"90% of {label} {q90:.0f} {unit} (+ {q90-q3:.0f} {unit}) [90th quantile]")
            msg.append(html.Br())
            msg.append(f"100% of {label} {q100:.0f} {unit} (+ {q100-q90:.0f} {unit}) [max]")
            msg.append(html.Br())
            msg.append(html.Br())
            msg.append(f"There are {len(stats_data)} Inference Services.")
            msg.append(html.Br())
            msg.append(f"The median load time is {med:.0f} {unit}.")
            msg.append(html.Br())
            q3_q1 = q3 - q1
            msg.append(f"There are {q3_q1:.0f} {unit} between Q1 and Q3 ({q3_q1/med*100:.1f}% of the median).")
            msg.append(html.Br())
            q100_q0 = q100 - q0
            msg.append(f"There are {q100 - q0:.0f} {unit} between min and max ({q100_q0/med*100:.1f}% of the median).")
            msg.append(html.Br())

        return fig, msg
