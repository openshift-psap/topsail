from collections import defaultdict
import re
import logging
import datetime
import math
import copy

import statistics as stats

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    InitTiming()

def generateInitServicesData(entries, variables, ordered_vars):
    data = []

    for entry in entries:
        for name, unit in entry.results.systemd_units.items():
            start = unit.get("Condition Timestamp")
            finish = unit.get("Active Enter Timestamp")
            if "target" in name: continue
            if "slide" in name: continue

            snc_service = name.startswith("crc-") or name.startswith("ocp-")
            if snc_service and False:
                print("==>", name)
                print("\n".join(f"{k}={v}" for k, v in unit.items()))
                print("---")
            if "n/a" in (start, finish):
                continue
            if None in (start, finish):
                continue

            short_duration = (finish-start).total_seconds() < 3

            if short_duration and not snc_service:
                continue

            data.append(dict(
                Name=name,
                Start=start,
                Finish=finish,
            ))

    return data


def generateInitTargetsData(entries, variables, ordered_vars):
    data = []

    for entry in entries:
        basic_target_time = None
        for name, unit in entry.results.systemd_units.items():
            if name != "basic.target": continue
            basic_target_time = unit.get("Active Enter Timestamp")

        for name, unit in entry.results.systemd_units.items():
            early_boot_visible = name in ("basic.target", "system.slice")
            if "target" not in name and not early_boot_visible: continue

            active = unit.get("Active Enter Timestamp")

            if "n/a" in (active, ):
                continue
            if None in (active,):
                continue
            early_boot = (active - basic_target_time).total_seconds() < 5

            if early_boot and not early_boot_visible:
                continue

            data.append(dict(
                Name=name,
                Time=active,
                Event=name,
            ))

    return data

class InitTiming():
    def __init__(self):
        self.name = "Init timing plot"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateInitServicesData(entries, variables, ordered_vars))

        if df.empty:
            return None, "Not data available ..."
        df = df.sort_values(by=["Start"])

        fig = px.timeline(df, x_start="Start", x_end="Finish", y="Name")

        entries = common.Matrix.all_records(settings, setting_lists)
        targets_df = pd.DataFrame(generateInitTargetsData(entries, variables, ordered_vars))
        targets_df = targets_df.sort_values(by=["Time"])

        fig.add_trace(go.Scatter(
            x=targets_df['Time'],
            y=targets_df['Name'],
            mode='markers',
            marker=dict(
            symbol='diamond',  # You can use 'circle', 'diamond', 'star', etc.
            size=16,
            color='red',
            line=dict(width=2, color='DarkSlateGrey')
            ),
            name='Milestones', # This name will appear in the legend
            #hovertemplate="<b>%{customdata[0]}</b><br>%{x|%Y-%m-%d}<extra></extra>",
            #customdata=targets_df[['Event']]
        ))

        plot_title = "CRC OpenShift init timing"

        fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
        fig.update_layout(title=plot_title, title_x=0.5,)
        fig.update_xaxes(title=f"")
        fig.update_layout(legend_title_text='')

        msg = []

        return fig, msg
