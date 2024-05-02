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
        cfg__check_all_thresholds = cfg.get("check_all_thresholds", False)
        cfg__time_to_reach_step = cfg.get("time_to_reach_step", "Go to JupyterLab Page")

        threshold_status_keys = set()
        entry_names = set()
        data = []

        for entry in common.Matrix.all_records(settings, setting_lists):
            entry_name = entry.get_name(variables)
            entry_names.add(entry_name)

            sort_index = entry.get_settings()[ordered_vars[0]] if len(variables) == 1 \
                else entry_name

            try: check_thresholds = entry.results.check_thresholds
            except AttributeError: check_thresholds = False

            if cfg__check_all_thresholds:
                check_thresholds = True

            if check_thresholds:
                threshold_status_keys.add(entry_name)

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
                thr90 = int(entry.get_threshold("launch_time_90", '0')) or None
                thr75 = int(entry.get_threshold("launch_time_75", '0')) or None

                data.append(dict(Version=entry_name,
                                SortIndex=sort_index,
                                LaunchTime90Threshold=thr90,
                                LaunchTime75Threshold=thr75,
                                Time=accumulated_timelength))

        if not data:
            return None, "No data found :/"

        df = pd.DataFrame(data).sort_values(by=["SortIndex"])

        fig = px.box(df, x="Version", y="Time", color="Version")
        has_thresholds = False

        if 'LaunchTime75Threshold' in df and not df['LaunchTime75Threshold'].isnull().all():
            fig.add_scatter(name="75% launch-time threshold",
                            x=df['Version'], y=df['LaunchTime75Threshold'], mode='lines+markers',
                            marker=dict(color='red', size=15, symbol="triangle-down"),
                            line=dict(color='black', width=3, dash='dot'))
            has_thresholds = True

        if 'LaunchTime90Threshold' in df and not df['LaunchTime90Threshold'].isnull().all():
            fig.add_scatter(name="90% launch-time threshold",
                            x=df['Version'], y=df['LaunchTime90Threshold'], mode='lines+markers',
                            marker=dict(color='red', size=15, symbol="triangle-down"),
                            line=dict(color='brown', width=3, dash='dot'))
            has_thresholds = True

        msg = []
        if has_thresholds:
            msg.append(html.H3("Time to launch the notebooks"))
        else:
            threshold_status_keys = []

        for entry_name in threshold_status_keys:
            res = df[df["Version"] == entry_name]
            if res.empty:
                msg.append(html.B(f"{entry_name}: no data ..."))
                msg.append(html.Br())
                continue

            threshold_90 = float(res["LaunchTime90Threshold"].values[0] or 0) or None
            value_90 = res["Time"].quantile(0.90)
            test90_passed = value_90 <= threshold_90

            threshold_75 = float(res["LaunchTime75Threshold"].values[0] or 0) or None
            value_75 = res["Time"].quantile(0.75)
            test75_passed = value_75 <= threshold_75

            status = [test90_passed, test75_passed]
            test_passed = all(status)
            success_count = len([s for s in status if s])
            msg += [html.B(entry_name), ": " if entry_name else "Test ", html.B("PASSED" if test_passed else "FAILED"), f" ({success_count}/{len(status)} success{'es' if success_count > 1 else ''})"]
            if test90_passed:
                msg.append(html.Ul(html.Li(f"PASS: {value_90:.0f} seconds <= launch_time_90={threshold_90:.0f} seconds")))
            else:
                msg.append(html.Ul(html.Li(f"FAIL: {value_90:.0f} seconds > launch_time_90={threshold_90:.0f} seconds")))

            if test75_passed:
                msg.append(html.Ul(html.Li(f"PASS: {value_75:.0f} seconds <= launch_time_75={threshold_75:.0f} seconds")))
            else:
                msg.append(html.Ul(html.Li(f"FAIL: {value_75:.0f} seconds > launch_time_75={threshold_75:.0f} seconds")))

        msg.append(html.H4("Median launch time"))
        for entry_name in sorted(entry_names):
            res = df[df["Version"] == entry_name]
            if res.empty:
                msg.append(html.Ul(html.Li(html.B(f"{entry_name}: no data ..."))))
                continue
            value_50 = res["Time"].quantile(0.50)
            msg.append(html.Ul(html.Li([html.B(f"{entry_name}:") if entry_name else "", f" {value_50:.0f} seconds"])))

            if entry_name in threshold_status_keys:
                for cmp_entry_name in sorted(entry_names):
                    if entry_name == cmp_entry_name: continue

                    cmp_res = df[df["Version"] == cmp_entry_name]
                    if cmp_res.empty:
                        continue
                    cmp_value_50 = cmp_res["Time"].quantile(0.50)
                    diff = value_50-cmp_value_50

                    comparator = "faster" if diff <= 0 else "slower"

                    pct = abs(diff/cmp_value_50*100)
                    msg.append(html.Ul(html.Ul(html.Li(f"{pct:.0f}% {comparator} than {cmp_entry_name} ({diff:+.0f} seconds)"))))

        fig.update_layout(title=f"Time to launch the notebooks", title_x=0.5,)
        fig.update_layout(yaxis_title="Launch time")
        fig.update_layout(xaxis_title="")

        return fig, msg
