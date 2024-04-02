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
    CompareCleanupSpeed()

class CompareTestSpeed():
    def __init__(self):
        self.name = "Compare Test Speed"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if not ordered_vars:
            return {}, "This plot cannot run without any variables ..."

        first_variable = ordered_vars[0]
        variables.remove(first_variable)

        text = []
        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            schedule_object_kind = "AppWrapper" if entry.results.test_case_properties.mode == "mcad" else "Job"

            test_cfg_setting = entry.settings.__dict__[first_variable]

            test_duration = (entry.results.test_start_end_time.end - entry.results.test_start_end_time.start).total_seconds() / 60
            name = entry.get_name(variables)
            text += [html.Code(f"{first_variable}={test_cfg_setting}{f' {name}' if variables else ''}"), html.Br()]

            def add_data(_what, speed):
                nonlocal text

                what = _what if not variables else \
                    f"{_what} | {name}"

                data.append(dict(
                    speed = speed,
                    what = what,
                ))
                data[-1][first_variable] = test_cfg_setting
                text += [f"• {_what}: {speed:.2f} {schedule_object_kind}s/minute", html.Br()]

            launch_speed = entry.results.test_case_properties.count / entry.results.test_case_properties.launch_duration
            add_data("Launch speed", launch_speed)

            processing_speed = entry.results.test_case_properties.count / test_duration
            add_data("Processing speed", processing_speed)

            if entry.results.pod_times:
                last_scheduled_pod_time = sorted(entry.results.pod_times, key=lambda t: t.pod_scheduled)[-1]
                start_to_last_scheduled_duration = (last_scheduled_pod_time.pod_scheduled - entry.results.test_start_end_time.start).total_seconds() / 60
                last_scheduled_speed = entry.results.test_case_properties.count / start_to_last_scheduled_duration
                add_data("Speed to last schedule", last_scheduled_speed)

            text += [html.Br()]

        df = pd.DataFrame(data)
        fig = px.line(df, x=first_variable, y="speed", color="what", markers=True)

        fig.update_layout(title=f"Comparison of the processing speed<br>over different {first_variable} values", title_x=0.5,)
        fig.update_layout(yaxis_title=f"Processing speed, in resources/minute ▸")
        fig.update_layout(xaxis_title=first_variable)

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

        var_list = ", ".join(variables)
        fig.update_layout(title=f"Comparison of the <i>actual</i> launch progress<br>for different {{{var_list}}} values", title_x=0.5,)
        fig.update_layout(yaxis_title="Number of resources ETCD-created")
        fig.update_layout(xaxis_title="Time since the beginning (in minutes)")

        return fig, html.P(text)


class CompareCleanupSpeed():
    def __init__(self):
        self.name = "Compare Cleanup Speed"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if not ordered_vars:
            return {}, "This plot cannot run without any variables ..."

        first_variable = ordered_vars[0]
        variables.remove(first_variable)

        text = []

        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            name = entry.get_name(variables)
            prev_time = None
            prev_event = None
            test_cfg_setting = entry.settings.__dict__[first_variable]

            text += [html.Code(f"{first_variable}={test_cfg_setting}{f' {name}' if variables else ''}"), html.Br()]

            if (mode := entry.results.test_case_properties.mode) != "mcad":
                text += [f"• {mode} mode enabled, cleanup time not relevant.", html.Br(), html.Br()]
                continue

            for event, time in sorted(entry.results.cleanup_times.__dict__.items(), key=lambda kv: kv[1]):
                if prev_time is not None:
                    duration = (time - prev_time).total_seconds() / 60
                    event_name = f"{prev_event} -> {event}"
                    if variables:
                        event_name += f" | {entry.get_name(variables)}"

                    data.append(dict(
                        Name = name,
                        Duration = duration,
                        Event = event_name,
                    ))
                    data[-1][first_variable] = test_cfg_setting
                    text += [f"• {prev_event} -> {event}: {duration:.1f} minutes", html.Br()]
                prev_time = time
                prev_event = event
            text.append(html.Br())

        df = pd.DataFrame(data)
        if df.empty:
            return None, "Not data available ..."

        if len(ordered_vars) == 1:
            fig = px.area(df, x=first_variable, y="Duration", color="Event", markers=True)
        else:
            fig = px.line(df, x=first_variable, y="Duration", color="Event", markers=True)

        var_list = ", ".join(ordered_vars)
        fig.update_layout(title=f"Comparison of the resource cleanup time<br>for different {{{var_list}}} values", title_x=0.5,)
        fig.update_layout(yaxis_title=f"⏴ Clean up time")
        fig.update_layout(xaxis_title=first_variable)

        return fig, html.P(text)
