from collections import defaultdict

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common


def register():
    LaunchTimeDistribution("Launch time distribution")
    LaunchTimeDistribution("Step successes", show_successes=True)


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
        expe_cnt = sum(1 for _ in common.Matrix.all_records(settings, setting_lists))

        cfg__all_in_one = cfg.get("all_in_one", False)
        cfg__show_only_step = cfg.get("show_only_step", False)

        if expe_cnt != 1 and not cfg__all_in_one:
            return {}, f"ERROR: only one experiment must be selected (found {expe_cnt}), or pass the all_in_one config flag."

        user_counts = set()
        threshold_status_keys = set()

        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            results = entry.results
            entry_name = ", ".join([f"{key}={entry.settings.__dict__[key]}" for key in variables])

            try: check_thresholds = entry.results.check_thresholds
            except AttributeError: check_thresholds = False

            user_counts.add(results.user_count)

            if cfg__all_in_one:
                success_users = sum(1 for exit_code in entry.results.ods_ci_exit_code.values() if exit_code == 0)
                failed_users = results.user_count - success_users
                data.append(dict(
                    Event=entry_name,
                    Count=success_users,
                    Status="PASS",
                    Threshold=int(entry.results.thresholds.get("test_successes")),
                ))

                if check_thresholds:
                    threshold_status_keys.add(entry_name)

                if failed_users:
                    data.append(dict(
                        Event=entry_name,
                        Count=failed_users,
                        Status="FAIL",
                        Threshold=int(entry.results.thresholds.get("test_successes")),
                ))
                continue

            for pod_name, ods_ci_output in entry.results.ods_ci_output.items():
                for step_name, step_status in ods_ci_output.items():
                    if not self.show_successes and step_status.status != "PASS":
                        continue
                    if cfg__show_only_step and cfg__show_only_step != step_name:
                        continue

                    data.append(dict(
                        Event=step_name + entry_name,
                        Time=step_status.start,
                        Count=1,
                        Status=step_status.status,
                    ))

        if not data:
            return None, "No data to plot ..."

        user_count = ", ".join(map(str, user_counts))

        df = pd.DataFrame(data)
        if self.show_successes:
            fig = px.histogram(df, x="Event", y="Count", color="Event", pattern_shape="Status")

            if "Threshold" in df and not df['Threshold'].isnull().all():
                fig.add_scatter(name="Pass threshold",
                                x=df['Event'], y=df['Threshold'], mode='lines+markers',
                                marker=dict(color='red', size=15, symbol="triangle-up"),
                                line=dict(color='black', width=3, dash='dot'))


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
        for idx, step_name in enumerate(entry.results.ods_ci_output[pod_name] if not cfg__all_in_one else []):
            step_times = df[df["Event"] == step_name]["Time"]

            if step_times.empty:
                msg.append(f"No result for step {idx}/{step_name}.")
                msg.append(html.Br())
                continue

            step_start_time = min(step_times)

            total_time = (step_times.quantile(1) - step_start_time).total_seconds() # 100%
            mid_80 = (step_times.quantile(0.90) - step_times.quantile(0.10)).total_seconds() # 10% <-> 90%
            mid_50 = (step_times.quantile(0.75) - step_times.quantile(0.25)).total_seconds() # 25% <-> 75%

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

        for legend_name in threshold_status_keys:
            res_ = df[df["Event"] == legend_name]
            res = res_[res_["Status"] == "PASS"]
            if len(res) != 1:
                logging.warning(f"Expected only one row for evaluating the threshold of '{legend_name}', got {len(res)} ...")
            pass_count = res["Count"].values[0]
            threshold = res["Threshold"].values[0]

            test_passed = pass_count >= threshold

            msg += [html.B(legend_name), ": ", html.B("PASSED" if test_passed else "FAILED"), f" ({'1' if test_passed else '0'}/1 success)"]
            if test_passed:
                msg.append(html.Ul(html.Li(f"PASS: {pass_count} >= threshold={threshold} successes")))
            else:
                msg.append(html.Ul(html.Li(f"FAIL: {pass_count} < threshold={threshold} successes")))


        return fig, msg
