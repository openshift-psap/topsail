from collections import defaultdict

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common


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
        threshold_status_keys = set()

        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            entry_name = ", ".join([f"{key}={entry.settings.__dict__[key]}" for key in variables])

            try: check_thresholds = entry.results.check_thresholds
            except AttributeError: check_thresholds = False

            if check_thresholds:
                threshold_status_keys.add(entry_name)

            for user_idx, ods_ci_output in entry.results.ods_ci_output.items():
                accumulated_timelength = 0

                for step_name, test_times in ods_ci_output.items():
                    if test_times.status != "PASS":
                        continue

                    timelength = (test_times.finish - test_times.start).total_seconds()

                    accumulated_timelength += timelength
                    if step_name != cfg__time_to_reach_step:
                        continue

                    break

                thr90 = int(entry.results.thresholds.get("launch_time_90", 0)) or None
                thr75 = int(entry.results.thresholds.get("launch_time_75", 0)) or None
                data.append(dict(Version=entry_name,
                                 LaunchTime90Threshold=thr90,
                                 LaunchTime75Threshold=thr75,
                                 Time=accumulated_timelength))

        if not data:
            return None, "No data found :/"

        df = pd.DataFrame(data).sort_values(by=["Version"])

        fig = px.box(df, x="Version", y="Time", color="Version")

        if 'LaunchTime75Threshold' in df and not df['LaunchTime75Threshold'].isnull().all():
            fig.add_scatter(name="75% launch-time threshold",
                            x=df['Version'], y=df['LaunchTime75Threshold'], mode='lines+markers',
                            marker=dict(color='red', size=15, symbol="triangle-down"),
                            line=dict(color='black', width=3, dash='dot'))

        if 'LaunchTime90Threshold' in df and not df['LaunchTime90Threshold'].isnull().all():
            fig.add_scatter(name="90% launch-time threshold",
                            x=df['Version'], y=df['LaunchTime90Threshold'], mode='lines+markers',
                            marker=dict(color='red', size=15, symbol="triangle-down"),
                            line=dict(color='brown', width=3, dash='dot'))
        msg = []
        for entry_name in threshold_status_keys:
            res = df[df["Version"] == entry_name]
            if res.empty:
                msg.append(html.B(f"{entry_name}: no data ..."))
                msg.append(html.Br())
                continue

            threshold_90 = float(res["LaunchTime90Threshold"].values[0])
            value_90 = res["Time"].quantile(0.90)
            test90_passed = value_90 <= threshold_90

            threshold_75 = float(res["LaunchTime75Threshold"].values[0])
            value_75 = res["Time"].quantile(0.75)
            test75_passed = value_75 <= threshold_75

            status = [test90_passed, test75_passed]
            test_passed = all(status)
            success_count = len([s for s in status if s])
            msg += [html.B(entry_name), ": ", html.B("PASSED" if test_passed else "FAILED"), f" ({success_count}/{len(status)} success{'es' if success_count > 1 else ''})"]
            if not test_passed:
                if not test90_passed:
                    msg.append(html.Ul(html.Li(f"FAIL: {value_90:.0f} seconds < launch_time_90={threshold_90:.0f} seconds")))
                if not test75_passed:
                    msg.append(html.Ul(html.Li(f"FAIL: {value_75:.0f} seconds < launch_time_75={threshold_75:.0f} seconds")))
            else:
                msg.append(html.Br())

        fig.update_layout(title=f"Time to launch the notebooks", title_x=0.5,)
        fig.update_layout(yaxis_title="Launch time")
        fig.update_layout(xaxis_title="")

        return fig, msg
