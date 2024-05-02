from collections import defaultdict
import statistics as stats

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html
import logging

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import spawntime
from ..store import utils

def register():
    LaunchTimeDistribution("Launch time distribution")
    LaunchTimeDistribution("Step successes", show_successes=True)
    RunTimeDistribution("Median runtime timeline")

class LaunchTimeDistribution():
    def __init__(self, name, show_successes=False):
        self.name = name
        self.id_name = name
        self.show_successes = show_successes

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        cfg__all_in_one = cfg.get("all_in_one", False)
        cfg__show_only_step = cfg.get("show_only_step", False)
        cfg__check_all_thresholds = cfg.get("check_all_thresholds", False)

        expe_cnt = common.Matrix.count_records(settings, setting_lists)

        if expe_cnt != 1 and not cfg__all_in_one:
            return {}, f"ERROR: only one experiment must be selected (found {expe_cnt}), or pass the all_in_one config flag."

        user_counts = set()
        threshold_status_keys = set()

        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            entry_name = entry.get_name(variables)

            try: check_thresholds = entry.results.check_thresholds
            except AttributeError: check_thresholds = False

            if cfg__check_all_thresholds:
                check_thresholds = True

            success_users, failed_users, total_users = utils.get_user_info(entry)
            user_counts.add(total_users)

            if cfg__all_in_one:
                if check_thresholds:
                    _threshold = entry.get_threshold("test_successes", "0")
                    if "%" in _threshold:
                        _threshold_pct = int(_threshold[:-1])
                        threshold = int(total_users * _threshold_pct / 100)
                    else:
                        threshold = int(_threshold) or None

                data.append(dict(
                    Event=entry_name,
                    Count=success_users,
                    Status="PASS",
                    Threshold=threshold if check_thresholds else None,
                ))

                if check_thresholds:
                    threshold_status_keys.add(entry_name)

                if failed_users:
                    data.append(dict(
                        Event=entry_name,
                        Count=failed_users,
                        Status="FAIL",
                        Threshold=threshold if check_thresholds else None,
                ))
                continue

            for user_index, step_name, step_status, step_time, step_start_time in utils.parse_users(entry):
                if not self.show_successes and step_status != "PASS":
                    continue
                if cfg__show_only_step and cfg__show_only_step != step_name:
                    continue

                if step_start_time is None: # LTS entry do not have the step start time
                    logging.error(f"Received step_start_time=None for entry {entry}, this is unexpected")

                data.append(dict(
                    Event=step_name + (entry_name if expe_cnt > 1 else ''),
                    Time=step_start_time,
                    Count=1,
                    Status=step_status,
                ))

        if not data:
            return None, "No data to plot ..."

        user_count = ", ".join(map(str, user_counts))
        has_thresholds = False
        df = pd.DataFrame(data)
        if self.show_successes:
            fig = px.histogram(df, x="Event", y="Count", color="Event", pattern_shape="Status")

            if "Threshold" in df and not df['Threshold'].isnull().all():
                fig.add_scatter(name="Pass threshold",
                                x=df['Event'], y=df['Threshold'], mode='lines+markers',
                                marker=dict(color='red', size=15, symbol="triangle-up"),
                                line=dict(color='black', width=3, dash='dot'))
                has_thresholds = True

            fig.update_layout(title=("Test" if cfg__all_in_one else "Step")
                              + f" successes for {user_count} users", title_x=0.5,)

            fig.update_layout(yaxis_title="Number of users")
            fig.update_layout(xaxis_title="")

        else:
            fig = px.box(df[df["Status"] == "PASS"], x="Event", y="Time", color="Event")
            fig.update_layout(title=f"Start time distribution for {user_count} users", title_x=0.5,)
            fig.update_layout(yaxis_title="Launch time")
            fig.update_layout(xaxis_title="")

        msg = []
        if cfg__all_in_one or utils.get_last_user(entry) :
            entries = []
        else:
            entries = utils.get_last_user_steps(entry) if utils.get_last_user(entry) else []

        for idx, step_name in enumerate(entries):
            step_times = df[df["Event"] == step_name]["Time"]

            if step_times.empty:
                msg.append(f"No result for step {idx}/{step_name}.")
                msg.append(html.Br())
                continue

            step_start_time = min(step_times)

            total_time = step_times.quantile(1) - step_start_time # 100%
            mid_80 = step_times.quantile(0.90) - step_times.quantile(0.10) # 10% <-> 90%
            mid_50 = step_times.quantile(0.75) - step_times.quantile(0.25) # 25% <-> 75%

            def time(sec):
                if sec <= 120:
                    return f"{sec:.0f} seconds"
                else:
                    return f"{sec/60:.1f} minutes"

            msg.append(f"All the users started the step {idx} within {time(total_time)}, ")
            msg.append(f"80% within {time(mid_80)}, ")
            msg.append(f"50% within {time(mid_50)}. ")
            msg.append(html.B(step_name))
            msg.append(html.Br())

        if has_thresholds:
            msg.append(html.H4(("Test" if cfg__all_in_one else "Step") + f" successes for {user_count} users"))
        else:
            threshold_status_keys = []

        for legend_name in threshold_status_keys:
            res_ = df[df["Event"] == legend_name]
            res = res_[res_["Status"] == "PASS"]
            if len(res) != 1:
                logging.warning(f"Expected only one row for evaluating the threshold of '{legend_name}', got {len(res)} ...")
            pass_count = res["Count"].values[0]
            threshold = res["Threshold"].values[0]

            test_passed = pass_count >= threshold

            msg += [html.B(legend_name), ": " if legend_name else "Test", html.B("PASSED" if test_passed else "FAILED"), f" ({'1' if test_passed else '0'}/1 success)"]
            if test_passed:
                msg.append(html.Ul(html.Li(f"PASS: {pass_count} >= threshold={threshold} successes")))
            else:
                msg.append(html.Ul(html.Li(f"FAIL: {pass_count} < threshold={threshold} successes")))


        return fig, msg


class RunTimeDistribution():
    def __init__(self, name, show_successes=False):
        self.name = name
        self.id_name = name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        user_counts = set()

        if not common.Matrix.has_records(settings, setting_lists):
            return None, "No experiments to plot"

        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            results = entry.results
            entry_name = ", ".join([f"{key}={entry.settings.__dict__[key]}" for key in variables])

            user_counts.add(results.user_count)

            for user_index, ods_ci in entry.results.ods_ci.items() if entry.results.ods_ci else []:
                if not ods_ci: continue

                for step_name, step_status in ods_ci.output.items():
                    if step_status.status != "PASS":
                        continue

                    data.append(dict(
                        UserCount=results.user_count,
                        Step=step_name + entry_name,
                        Time=(step_status.finish - step_status.start).total_seconds(),
                    ))

        data = spawntime.add_ods_ci_output(entry, keep_failed_steps=False, hide_failed_users=True, hide=None)

        if not data:
            return None, "No data to plot ..."

        data_df = pd.DataFrame(data)

        stats_data = []
        base_value = 0
        steps = data_df["Step Name"].unique()
        notebook_ready_time = None
        msg = []
        for step_name in steps:
            step_df = data_df[data_df["Step Name"] == step_name]
            q1, median, q3 = stats.quantiles(step_df["Step Duration"])
            q1_dist = median-q1
            q3_dist = q3-median
            stats_data.append(dict(
                Steps=step_name,
                MedianDuration=median,
                Q1=q1_dist,
                Q3=q3_dist,
                UserCount=str(entry.results.user_count),
                Base=base_value,
            ))

            q1_txt = f"-{q1_dist:.0f}s" if round(q1_dist) >= 2 else ""
            q3_txt = f"+{q3_dist:.0f}s" if round(q3_dist) >= 2 else ""
            msg += [f"{step_name}: {median:.0f}s {q1_txt}{q3_txt}", html.Br()]

            base_value += median
            if step_name.endswith("Go to JupyterLab Page"):
                notebook_ready_time = base_value
                msg += ["---", html.Br()]

        stats_df = pd.DataFrame(stats_data)

        fig = px.bar(stats_df,
                     x="MedianDuration", y="Steps", color="Steps", base="Base",
                     error_x_minus="Q1", error_x="Q3",
                     title="Median runtime timeline")

        if notebook_ready_time:
            fig.add_scatter(name="Time to reach JupyterLab",
                            x=[notebook_ready_time, notebook_ready_time],
                            y=[steps[0], steps[-1]])
        fig.update_layout(xaxis_title="Timeline (in seconds). Error bars show Q1 and Q3.")
        fig.update_layout(yaxis_title="", title_x=0.5,)

        return fig, msg
