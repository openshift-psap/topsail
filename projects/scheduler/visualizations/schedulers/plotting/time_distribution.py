from collections import defaultdict

import statistics as stats

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    ExecutionDistribution()
    WaitingTimeDistribution()
    WaitingTimeTimeline()
    SchedulingOrder()

def generateTimeInState(entry):
    data = []
    for resource_times in entry.results.resource_times.values():

        current_name = None
        current_start = None
        for condition_name, condition_ts in resource_times.conditions.items():
            if current_name:
                data.append(dict(
                    Name=resource_times.name,
                    State=f"{current_name}",
                    Start=current_start,
                    Finish=condition_ts,
                    Duration=(condition_ts - current_start).total_seconds(),
                ))
            current_name = condition_name
            current_start = condition_ts

        if current_name:
            data.append(dict(
                Name=resource_times.name,
                State=current_name,
                Start=current_start,
                Finish=entry.results.test_start_end_time.end, # last state lives until the end of the test
                Duration=(entry.results.test_start_end_time.end - current_start).total_seconds(),
            ))
    return data


class ExecutionDistribution():
    def __init__(self):
        self.name = "Execution time distribution"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        cnt = common.Matrix.count_records(settings, setting_lists)
        if cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            break

        cfg__show_only_state = cfg.get("state", False)

        data = generateTimeInState(entry)

        if not data:
            return None, "No data to plot ..."

        df = pd.DataFrame(data)

        if cfg__show_only_state:
            df = df[df.State == cfg__show_only_state]

        fig = px.histogram(df, x="Duration",
                           color="State",
                           marginal="box",
                           barmode="overlay",
                           hover_data=df.columns)
        fig.update_layout(xaxis_title="Step timelength (in seconds)")

        if cfg__show_only_state:
            title = f"Distribution of the time spent<br>in the <b>{cfg__show_only_state}</b> state"
            fig.layout.update(showlegend=False)
        else:
            title = f"Distribution of the time spent in each of the different state"

        fig.update_layout(title=title, title_x=0.5)

        msg = []
        if cfg__show_only_state and len(df) >= 2:
            q1, med, q3 = stats.quantiles(df.Duration)
            q90 = stats.quantiles(df.Duration, n=10)[8] # 90th percentile
            q100 = df.Duration.max()

            def time(sec):
                if sec < 0.001:
                    return f"0 seconds"
                elif sec < 5:
                    return f"{sec:.3f} seconds"
                if sec < 20:
                    return f"{sec:.1f} seconds"
                elif sec <= 120:
                    return f"{sec:.0f} seconds"
                else:
                    return f"{sec/60:.1f} minutes"

            msg += [f"{len(df)} {entry.results.target_kind_name}s went in the ", html.B(cfg__show_only_state), " state."]
            msg.append(html.Br())
            msg += [f"It took them ", html.B(f"between {time(df.Duration.min())} and {time(df.Duration.max())}"), " to complete this step."]
            msg.append(html.Br())
            msg.append(f"25% of the {entry.results.target_kind_name} were in this state during {time(q1)} [Q1]")
            msg.append(html.Br())
            msg.append(f"50% of the {entry.results.target_kind_name} were in this state during {time(med)} (+ {time(med-q1)}) [median]")
            msg.append(html.Br())
            msg.append(f"75% of the {entry.results.target_kind_name} were in this state during {time(q3)} (+ {time(q3-med)}) [Q3]")
            msg.append(html.Br())
            msg.append(f"90% of the {entry.results.target_kind_name} were in this state during {time(q90)} (+ {time(q90-q3)}) [90th quantile]")
            msg.append(html.Br())
            msg.append(f"There are {time(q3 - q1)} between Q1 and Q3.")
            msg.append(html.Br())
            msg.append(f"There are {time(q100 - q3)} between Q3 and Q4.")
            msg.append(html.Br())

        return fig, msg

def generateWaitingTimeDistribution(entry):
    data = []
    missing = 0

    for resource_times in entry.results.resource_times.values():
        if resource_times.kind.lower() != entry.results.test_case_properties.resource_kind: continue
        try:
            waiting_time = (resource_times.start - resource_times.creation).total_seconds() / 60

            data.append(dict(waiting_time=waiting_time, name=resource_times.name))
        except Exception:
            missing += 1
            pass

    return missing, data


class WaitingTimeDistribution():
    def __init__(self):
        self.name = "Waiting Time Distribution"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        expe_cnt = common.Matrix.count_records(settings, setting_lists)
        if expe_cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {expe_cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            pass # entry is set

        missing, data = generateWaitingTimeDistribution(entry)

        if not data:
            return None, "No data to plot ..."

        df = pd.DataFrame(data)

        fig = px.histogram(df, x="waiting_time",
                           marginal="box",
                           barmode="overlay",
                           hover_data=df.columns)

        fig.update_yaxes(title="Number of objects")
        fig.update_xaxes(title="Waiting time, in minutes after the start time")

        fig.update_layout(title=f"{entry.results.target_kind_name} Waiting Time", title_x=0.5)

        msg = []
        if missing != 0:
            msg += [f"{missing} {entry.results.target_kind_name} didn't run to completion."]

        return fig, msg


class WaitingTimeTimeline():
    def __init__(self):
        self.name = "Waiting Time Timeline"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        expe_cnt = common.Matrix.count_records(settings, setting_lists)
        if expe_cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {expe_cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            pass # entry is set

        missing, data = generateWaitingTimeDistribution(entry)

        if not data:
            return None, "No data to plot ..."

        df = pd.DataFrame(data)
        df = df.sort_values(by=["name"])
        fig = px.bar(df, x="name", y="waiting_time",
                     hover_data=df.columns)

        fig.update_yaxes(title="Wait duration")
        fig.update_xaxes(title="Waiting time, in minutes after the start time")

        fig.update_layout(title=f"{entry.results.target_kind_name} Waiting Time", title_x=0.5)

        msg = []
        if missing != 0:
            msg += [f"{missing} {entry.results.target_kind_name} didn't run to completion."]

        return fig, msg


def generateSchedulingOrder(entry):
    data = []

    for resource_times in entry.results.resource_times.values():
        if resource_times.kind.lower() != entry.results.test_case_properties.resource_kind: continue
        try:
            start_time = resource_times.start
            resource_id = int(resource_times.name.split("-")[-1])
            data.append(dict(start_time=start_time, resource_id=resource_id,
                             resource_name=resource_times.name))
        except Exception:
            pass

    return data


class SchedulingOrder():
    def __init__(self):
        self.name = "Scheduling Order"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        expe_cnt = common.Matrix.count_records(settings, setting_lists)
        if expe_cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {expe_cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            pass # entry is set

        data = generateSchedulingOrder(entry)

        if not data:
            return None, "No data to plot ..."

        df = pd.DataFrame(data)
        df = df.sort_values(by=["start_time"])
        df['start_idx'] = range(len(df))

        fig = px.bar(df, x="start_idx", y="resource_id",
                     hover_data=df.columns)

        fig.update_yaxes(title="Resource ID")
        fig.update_xaxes(title="Start index")

        fig.update_layout(title=f"{entry.results.target_kind_name} Start Order", title_x=0.5)

        return fig, []
