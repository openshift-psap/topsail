from collections import defaultdict
import re
import logging
import datetime
import math
import copy

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import progress

def register():
    CompareTestSpeed()
    CompareLaunchSpeed()


class CompareTestSpeed():
    def __init__(self):
        self.name = "Compare Test Speed"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        if len(variables) != 1:
            return None, f"{self.name} only works with one variable. Got {len(variables)}: {', '.join(variables)}"

        variable = list(variables)[0]

        text = []
        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            schedule_object_kind = "Job" if entry.results.test_case_properties.job_mode else "AppWrapper"

            test_cfg_setting = entry.settings.__dict__[variable]

            test_duration = (entry.results.test_start_end_time.end - entry.results.test_start_end_time.start).total_seconds() / 60

            text += [html.Code(f"{variable}={test_cfg_setting}")]
            def add_data(what, speed):
                data.append(dict(
                    speed = speed,
                    what = what,
                ))
                data[-1][variable] = test_cfg_setting
                text.append(f" | {what}: {speed:.2f} {schedule_object_kind}s/minutes")

            launch_speed = entry.results.test_case_properties.aw_count / entry.results.test_case_properties.launch_duration
            add_data("Launch speed", launch_speed)

            processing_speed = entry.results.test_case_properties.aw_count / test_duration
            add_data("Processing speed", processing_speed)

            if entry.results.pod_times:
                last_scheduled_pod_time = sorted(entry.results.pod_times, key=lambda t: t.pod_scheduled)[-1]
                start_to_last_scheduled_duration = (last_scheduled_pod_time.pod_scheduled - entry.results.test_start_end_time.start).total_seconds() / 60
                last_scheduled_speed = entry.results.test_case_properties.aw_count / start_to_last_scheduled_duration
                add_data("Speed to last schedule", last_scheduled_speed)

            text += [html.Br()]

        df = pd.DataFrame(data)
        fig = px.line(df, x=variable, y="speed", color="what", markers=True)

        fig.update_layout(title=f"Comparison of the processing speed<br>over different {variable} values", title_x=0.5,)
        fig.update_layout(yaxis_title=f"Processing speed, in {schedule_object_kind}s/minutes ▸")
        fig.update_layout(xaxis_title=variable)

        return fig, html.P(text)


class CompareLaunchSpeed():
    def __init__(self):
        self.name = "Compare Launch Speed"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        if len(variables) != 1:
            return None, f"{self.name} only works with one variable. Got {len(variables)}: {', '.join(variables)}"

        variable = list(variables)[0]

        text = []

        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):

            entry_data = progress.generate_launch_progress_data(entry)
            for entry_datum in entry_data:
                entry_datum["Name"] = entry.get_name(variables)
            entry_data.pop()
            data += entry_data

        df = pd.DataFrame(data)
        fig = px.line(df, x="Delta", y="Count", color="Name")

        fig.update_layout(title=f"Comparison of the <i>actual</i> launch progress<br>for different {variable} values", title_x=0.5,)
        fig.update_layout(yaxis_title="Number of resources ETCD-created")
        fig.update_layout(xaxis_title="Time since the beginning (in minutes)")

        return fig, html.P(text)
