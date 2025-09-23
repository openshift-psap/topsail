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
    SystemdInitTiming()
    OCPTiming()


def get_start_end_time(entries, *, absolute):
    midnight = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for entry in entries:
        try:
            vm_start_time = entry.results.systemd_units["system.slice"]['Active Enter Timestamp']
        except KeyError:
            logging.error(f"'system.slice' not found, cannot generate the init services data for entry {entry.settings}")
            continue

        try:
            crc_ready_time = entry.results.systemd_units["crc-custom.target"]['Active Enter Timestamp']
        except KeyError:
            logging.error(f"'crc-custom.target' not found, cannot generate the init services data for entry {entry.settings}")
            continue

        if absolute:
            return vm_start_time, crc_ready_time
        else:
            return midnight, midnight + (crc_ready_time - vm_start_time)


def generateInitServicesData(entries, variables, ordered_vars):
    data = []
    midnight = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    MUST_BE_SHOWN_NAMES = [
        "ovs-configuration.service",
        "gv-user-network@tap0.service",
        "cloud-init.service",
        "kubelet.service",
    ]

    for entry in entries:
        try:
            vm_start_time = entry.results.systemd_units["system.slice"]['Active Enter Timestamp']
        except KeyError:
            logging.error(f"'system.slice' not found, cannot generate the init services data for entry {entry.settings}")
            continue

        for name, unit in entry.results.systemd_units.items():
            if "target" in name: continue
            if "slice" in name: continue

            start_time = unit.get("Condition Timestamp")
            finish_time = unit.get("Active Enter Timestamp")
            if finish_time in (None, "n/a"):
                finish_time = unit.get("Inactive Enter Timestamp")

            snc_service = name.startswith("crc-") or name.startswith("ocp-")
            must_be_shown = snc_service
            must_be_shown |= name in MUST_BE_SHOWN_NAMES

            if snc_service and False:
                print("==>", name)
                print("\n".join(f"{k}={v}" for k, v in unit.items()))
                print("---")
            if "n/a" in (start_time, finish_time):
                continue
            if None in (start_time, finish_time):
                continue

            start = start_time - vm_start_time
            finish = finish_time - vm_start_time

            short_duration = (finish-start).total_seconds() < 3
            if finish == start:
                finish += datetime.timedelta(seconds=0.5)

            if short_duration and not must_be_shown:
                continue

            data.append(dict(
                Name=name,
                Start=(midnight + start),
                Finish=(midnight + finish),
                Duration=f"{(finish-start).total_seconds():.0f}s",
            ))

    return data


def generateInitTargetsData(entries, variables, ordered_vars):
    data = []
    midnight = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for entry in entries:
        try:
            vm_start_time = entry.results.systemd_units["system.slice"]['Active Enter Timestamp']
        except KeyError:
            logging.error(f"'system.slice' not found, cannot generate the init services data for entry {entry.settings}")
            continue

        try:
            basic_target_time = entry.results.systemd_units["basic.target"]['Active Enter Timestamp']
        except KeyError:
            logging.error(f"'system.slice' not found, cannot generate the init services data for entry {entry.settings}")
            continue

        for name, unit in entry.results.systemd_units.items():
            early_boot_visible = name in ("", "system.slice")
            if "target" not in name and not early_boot_visible: continue

            active_time = unit.get("Active Enter Timestamp")

            if "n/a" in (active_time, ):
                continue
            if None in (active_time,):
                continue

            active = active_time - vm_start_time
            early_boot = active.total_seconds() < 5

            if early_boot and not early_boot_visible:
                continue

            data.append(dict(
                Name=name,
                Time=midnight + active,
                Event=name,
            ))

    return data


class SystemdInitTiming():
    def __init__(self):
        self.name = "SystemD Init timing plot"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        entries = list(common.Matrix.all_records(settings, setting_lists))

        if len(entries) != 1:
            return None, f"Must have exactly 1 entry, found {len(entries)} ..."

        df = pd.DataFrame(generateInitServicesData(entries, variables, ordered_vars))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["Start"])

        fig = px.timeline(df, x_start="Start", x_end="Finish", y="Name", hover_data=df.columns)

        vm_start_time, crc_ready_time = get_start_end_time(entries, absolute=False)
        fig.add_vline(x=vm_start_time, line_width=3, line_dash="dash", line_color='orange', name='VM Start Time', showlegend=True)
        fig.add_vline(x=crc_ready_time, line_width=3, line_dash="dash", line_color='green', name='CRC Ready Time', showlegend=True)

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
        ))

        plot_title = "CRC SystemD init timing"

        fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
        fig.update_layout(title=plot_title, title_x=0.5,)
        fig.update_xaxes(title=f"")
        fig.update_layout(legend_title_text='')

        msg = "<br>".join(entries[0].results.systemd_crc_critical_chain.text.split("\n")).replace("  ", "&nbsp;"*2)

        return fig, msg


def coIsReady(co):
    status = {}

    for cond in co["status"]["conditions"]:
        lastTransitionTime = datetime.datetime.strptime(cond["lastTransitionTime"], '%Y-%m-%dT%H:%M:%SZ')

        if cond["type"] == "Available":
            if cond["status"] != "True":
                status["not available"] = lastTransitionTime
            elif cond["status"] == "True":
                status["available"] = lastTransitionTime
            continue
        elif cond["type"] == "Degraded":
            if cond["status"] == "True":
                status["degraded"] = lastTransitionTime
            continue
        elif cond["type"] == "Progressing":
            if cond["status"] == "True":
                status["progressing"] = lastTransitionTime
            continue
        elif cond["type"] == "Upgradeable":
            continue
        elif cond["type"] == "EvaluationConditionsDetected":
            continue
        elif cond["type"] == "Disabled":
            if cond["status"] == "True":
                status["disabled"] = lastTransitionTime
            continue
        elif cond["type"] == "ManagementStateDegraded":
            continue
        elif cond["type"] == "RecentBackup":
            continue
        else:
            print(co["metadata"]["name"], "has an unexpected condition:", cond)


    return status


def generateOcpCoData(entries, variables, ordered_vars):
    data = []
    midnight = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    vm_start_time, crc_ready_time = get_start_end_time(entries, absolute=True)

    last_co_ready = None
    last_co_ready_name = None

    for entry in entries:
        for co_entry in entry.results.ocp_co:
            status = coIsReady(co_entry)
            for state, transit_time in status.items():
                if vm_start_time > transit_time:
                    state_time = midnight
                    continue
                else:
                    state_time = midnight + (transit_time - vm_start_time)

                co_name = co_entry["metadata"]["name"]
                if last_co_ready is None or state_time > last_co_ready:
                    last_co_ready = state_time
                    last_co_ready_name = co_name

                data.append(dict(
                    ClusterOperator=co_name,
                    State=state,
                    Time=state_time,
            ))

    data.append(dict(
        ClusterOperator="CRC Ready",
        State="available",
        Time=(midnight + (crc_ready_time - vm_start_time)),
    ))

    return data, (last_co_ready, last_co_ready_name)


class OCPTiming():
    def __init__(self):
        self.name = "OpenShift Init timing plot"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        entries = list(common.Matrix.all_records(settings, setting_lists))

        data, last_co_ready = generateOcpCoData(entries, variables, ordered_vars)
        df = pd.DataFrame(data)

        if df.empty:
            return None, "Not data available ..."
        df = df.sort_values(by=["Time"])

        # Create plotly scatter plot

        fig = px.scatter(df,
                         x='Time',
                         y='ClusterOperator',
                         color='State',
                         title='Cluster Operator States Over Time')

        vm_start_time, crc_ready_time = get_start_end_time(entries, absolute=False)
        fig.add_vline(x=vm_start_time, line_width=3, line_dash="dash", line_color='orange', name='VM Start Time', showlegend=True)
        fig.add_vline(x=crc_ready_time, line_width=3, line_dash="dash", line_color='green', name='CRC Ready Time', showlegend=True)

        plot_title = "CRC OpenShift init timing"

        fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
        fig.update_layout(title=plot_title, title_x=0.5,)
        fig.update_xaxes(title=f"")
        fig.update_layout(legend_title_text='')

        msg = []

        if last_co_ready and last_co_ready[0]:
            msg += [f"The last ClusterOperator became ready was ", html.B(last_co_ready[1]), f" after {last_co_ready[0].time()}."]
            msg += [html.Br()]
            crc_ready_after_co = (crc_ready_time - last_co_ready[0]).total_seconds()
            msg += [f"The CRC became ready at {crc_ready_time.time()}, that is, {crc_ready_after_co:.0f}s after the last CO."]

        return fig, msg
