from collections import defaultdict
import re
import logging
import datetime

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    MappingTimeline("Pod/Node timeline: Test Pods", is_notebook=False)
    MappingTimeline("Pod/Node timeline: Notebooks", is_notebook=True)

    MappingDistribution("Pod/Node distribution: Test Pods", is_notebook=False)
    MappingDistribution("Pod/Node distribution: Notebooks", is_notebook=True)

    MappingPerformance("Pod/Node performance index: Test Pods", is_notebook=False)
    MappingPerformance("Pod/Node performance index: Notebooks", is_notebook=True)

    TestNodesPerformance("Test nodes test duration")


def generate_data(entry, cfg, is_notebook, force_order_by_user_idx=False):
    test_nodes = {}
    entry_results = entry.results

    if is_notebook:
        hostnames = entry_results.notebook_hostnames
        all_pod_times = entry_results.notebook_pod_times
    else:
        hostnames = entry_results.testpod_hostnames
        all_pod_times = entry_results.testpod_times

    hostnames_index = list(hostnames.values()).index

    data = []

    if force_order_by_user_idx:
        for user_idx in range(entry.results.user_count):
            data.append(dict(
                UserIndex = f"User #{user_idx:04d}",
                UserIdx = user_idx,
                PodStart = entry_results.tester_job.creation_time,
                PodFinish = entry_results.tester_job.creation_time,
                NodeIndex = f"Not mapped",
                NodeName = f"Not mapped",
                Count=0,
            ))

    for pod_times in all_pod_times.values():
        user_idx = pod_times.user_index
        pod_name = pod_times.pod_name

        try:
            if is_notebook:
                open_step = entry.results.ods_ci[user_idx].output["Open the Browser"]
                performanceIndex = (open_step.finish - open_step.start).total_seconds()
            else:
                performanceIndex = max(entry.results.ods_ci[user_idx].notebook_benchmark["measures"])

        except Exception:
            performanceIndex = None

        try:
            hostname = hostnames[user_idx]
            if not hostname: raise KeyError # not mapped
        except KeyError:
            data.append(dict(
                UserIndex = f"User #{user_idx:04d}",
                UserIdx = user_idx,
                PodStart = entry_results.tester_job.creation_time,
                PodFinish = entry_results.tester_job.completion_time,
                NodeIndex = f"No node",
                NodeName = f"No node",
                PerformanceIndex = performanceIndex,
                Count=1,
            ))
            continue

        shortname = hostname.replace(".compute.internal", "").replace(".us-west-2", "")
        if "container_finished" in pod_times.__dict__:
            finish = pod_times.container_finished
        elif "last_activity" in pod_times.__dict__ and pod_times.last_activity:
            finish = pod_times.last_activity
        else:
            finish = entry_results.tester_job.completion_time

        try:
            instance_type = entry.results.nodes_info[hostname].instance_type
        except (AttributeError, KeyError):
            instance_type = ""

        data.append(dict(
            UserIndex = f"User #{user_idx:04d}",
            UserIdx = user_idx,
            PodStart = pod_times.start_time,
            PodFinish = finish,
            NodeIndex = f"Node {hostnames_index(hostname)}",
            NodeName = f"Node {hostnames_index(hostname)}<br>{shortname}" + (f"<br>{instance_type}" if instance_type != "N/A" else ""),
            PerformanceIndex = performanceIndex,
            Count=1,
        ))

    return data

class MappingTimeline():
    def __init__(self, name, is_notebook):
        self.name = name
        self.id_name = name
        self.is_notebook = is_notebook

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if common.Matrix.count_records(settings, setting_lists) != 1:
            return {}, "ERROR: only one experiment must be selected"

        cfg__force_order_by_user_idx = cfg.get("force_order_by_user_idx", False)

        df = None
        for entry in common.Matrix.all_records(settings, setting_lists):
            df = pd.DataFrame(generate_data(entry, cfg, self.is_notebook,
                                            force_order_by_user_idx=cfg__force_order_by_user_idx))

        if df.empty:
            return None, "Not data available ..."

        fig = px.timeline(df, x_start="PodStart", x_end="PodFinish", y="UserIndex", color="NodeIndex")

        for fig_data in fig.data:
            if fig_data.x[0].__class__ is datetime.timedelta:
                # workaround for Py3.9 error:
                # TypeError: Object of type timedelta is not JSON serializable
                fig_data.x = [v.total_seconds() * 1000 for v in fig_data.x]

        fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
        fig.update_layout(barmode='stack', title=f"Mapping of the {'Notebook' if self.is_notebook else 'Test'} Pods on the nodes", title_x=0.5,)
        fig.update_layout(yaxis_title="")
        fig.update_layout(xaxis_title="Timeline (by date)")

        return fig, ""

class MappingDistribution():
    def __init__(self, name, is_notebook):
        self.name = name
        self.id_name = name
        self.is_notebook = is_notebook

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if common.Matrix.count_records(settings, setting_lists) != 1:
            return {}, "ERROR: only one experiment must be selected"

        df = None
        for entry in common.Matrix.all_records(settings, setting_lists):
            df = pd.DataFrame(generate_data(entry, cfg, self.is_notebook))

        if df.empty:
            return None, "Nothing to plot (no data)"

        # sort by UserIndex to improve readability
        df = df.sort_values(by=["UserIdx"])

        fig = px.bar(df, x="NodeName", y="Count", color="UserIdx",
                     title=f"Distribution of the {'Notebook' if self.is_notebook else 'Test'} Pods on the nodes")

        fig.update_layout(title_x=0.5,)
        fig.update_layout(xaxis_title="")
        fig.update_layout(yaxis_title="Pod count")
        fig.update_yaxes(tick0=0, dtick=1)
        return fig, ""

class MappingPerformance():
    def __init__(self, name, is_notebook):
        self.name = name
        self.id_name = name
        self.is_notebook = is_notebook

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if common.Matrix.count_records(settings, setting_lists) != 1:
            return {}, "ERROR: only one experiment must be selected"

        df = None
        for entry in common.Matrix.all_records(settings, setting_lists):
            df = pd.DataFrame(generate_data(entry, cfg, self.is_notebook))

        if df.empty:
            return None, "Nothing to plot (no data)"

        # sort by UserIndex to improve readability
        df = df.sort_values(by=["UserIndex"])

        title = (f"Performance of the {'Notebook' if self.is_notebook else 'Test'} Pods on the nodes" +
                 f"<br><sup>" + ("(Python benchmark results)" if self.is_notebook else "(browser loading times)") + "</sup>")
        fig = px.box(df, x="NodeName", y="PerformanceIndex",
                     title=title)

        fig.update_layout(title_x=0.5,)
        fig.update_layout(xaxis_title="")
        fig.update_layout(yaxis_title="Pod performance index")
        fig.update_yaxes(tick0=0, dtick=1)
        return fig, ""


class TestNodesPerformance():
    def __init__(self, name):
        self.name = name
        self.id_name = name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if common.Matrix.count_records(settings, setting_lists) != 1:
            return {}, "ERROR: only one experiment must be selected"

        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            hostnames = entry.results.testpod_hostnames
            hostnames_index = list(hostnames.values()).index

            for user_idx, ods_ci in entry.results.ods_ci.items():
                if not ods_ci: continue
                if not ods_ci.progress: continue

                failures = ods_ci.exit_code
                try:
                    test_start_time = ods_ci.progress["launch_delay"]
                    test_finish_time = ods_ci.progress["test_execution"]
                except KeyError as e:
                    logging.warning(f"User #{user_idx} key error: {e}")
                    continue

                test_duration = test_finish_time - test_start_time

                hostname = hostnames.get(user_idx, "mapping not found")
                shortname = hostname.replace(".compute.internal", "").replace(".us-west-2", "")
                try:
                    hostname_idx = hostnames_index(hostname)
                except ValueError:
                    hostname_idx = -1

                data.append(dict(
                    Status="PASS" if ods_ci.exit_code == 0 else "FAIL",
                    Duration = test_duration.total_seconds(),
                    User = f"User #{user_idx:04d}",
                    NodeIndex = f"Node {hostname_idx}",
                    NodeName = f"Node {hostname_idx}<br>{shortname}",
                ))

        if not data:
            return None, "Nothing to plot (no data)"

        df = pd.DataFrame(data).sort_values(by=["Duration"], ascending=True)

        title = f"Duration of the user test on each of the test nodes"
        fig = px.bar(df, x="User", y="Duration", color="NodeName",
                     title=title)

        fig.update_layout(title_x=0.5,)
        fig.update_layout(xaxis_title="")
        fig.update_layout(yaxis_title="Test duration")

        return fig, ""
