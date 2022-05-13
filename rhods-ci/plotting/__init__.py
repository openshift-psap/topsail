from collections import defaultdict

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    Plot("Gantt")

class Plot():
    def __init__(self, name):
        self.name = name
        self.id_name = name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, params, param_lists, variables, cfg):

        all_XY = defaultdict(dict)
        info = defaultdict(dict)
        user_count = 0

        if sum(1 for _ in common.Matrix.all_records(params, param_lists)) != 1:
            return {}, "ERROR: only one experiment must be selected"

        data = []
        for entry in common.Matrix.all_records(params, param_lists):
            user_count = len(entry.results.test_pods)
            test_nodes = {}
            for i, nodename in enumerate(entry.results.testpod_hostnames.values()):
                test_nodes[nodename] = f"Test node #{i}"

            rhods_nodes = {}
            for i, nodename in enumerate(entry.results.notebook_hostnames.values()):
                rhods_nodes[nodename] = f"RHODS node #{i}"

            for testpod_name in entry.results.test_pods:
                idx = int(testpod_name.split("-")[2])
                name = f"User #{idx}"

                pod_times = entry.results.pod_times[testpod_name]
                event_times = entry.results.event_times[testpod_name]
                notebook_name = f"jupyterhub-nb-testuser{idx}"
                try:
                    notebook_node = rhods_nodes[entry.results.notebook_hostnames[notebook_name]]
                except KeyError:
                    notebook_node = "<no RHODS node>"

                common_props = dict(Resource=notebook_node + "<br>" + name, Node=notebook_node)

                data.append(dict(**common_props, Task="01. Test pod creation",  Start=entry.results.job_creation_time, Finish=pod_times.start_time))
                data.append(dict(**common_props, Task="02. Test pod scheduling", Start=data[-1]["Finish"], Finish=event_times.scheduled))
                data.append(dict(**common_props, Task="03. Test pod image pull", Start=data[-1]["Finish"], Finish=event_times.pulling))
                data.append(dict(**common_props, Task="04. Test pod initialization", Start=data[-1]["Finish"], Finish=pod_times.container_started))
                data.append(dict(**common_props, Task="05. Test Execution",      Start=data[-1]["Finish"], Finish=pod_times.container_finished))

                info[name]["test_container_started"] = pod_times.container_started


        for entry in common.Matrix.all_records(params, param_lists):
            for notebook_name in entry.results.notebook_pods:
                idx = int(notebook_name.replace("jupyterhub-nb-testuser", ""))
                name = f"User #{idx}"

                pod_times = entry.results.pod_times[notebook_name]
                event_times = entry.results.event_times[notebook_name]
                try:
                    notebook_node = rhods_nodes[entry.results.notebook_hostnames[notebook_name]]
                except KeyError:
                    notebook_node = "None"

                common_props = dict(Resource=notebook_node + "<br>" + name, Node=rhods_nodes[entry.results.notebook_hostnames[notebook_name]])

                data.append(dict(**common_props, Task="10. ODS-CI Test initialization", Start=info[name]["test_container_started"], Finish=event_times.appears_time))

                data.append(dict(**common_props, Task="20. Notebook scheduling",        Start=data[-1]["Finish"], Finish=event_times.scheduled))
                data.append(dict(**common_props, Task="21. Notebook preparation",       Start=data[-1]["Finish"], Finish=event_times.pulling))
                data.append(dict(**common_props, Task="22. Notebook image pull",        Start=data[-1]["Finish"], Finish=event_times.pulled))
                data.append(dict(**common_props, Task="23. Notebook initialization",    Start=data[-1]["Finish"], Finish=event_times.started))
                data.append(dict(**common_props, Task="24. Notebook execution",         Start=data[-1]["Finish"], Finish=event_times.terminated))

        data.insert(0, dict(Resource="Test Job<br>lifespan", Task="-- Test job lifespan", Start=entry.results.job_creation_time, Finish=entry.results.job_completion_time, Node="None"))

        fig = px.timeline(pd.DataFrame(data), x_start="Start", x_end="Finish", y="Resource", color="Task")
        fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
        fig.update_layout(barmode='stack', title=f"Execution timeline of {user_count} users launching a notebook ", title_x=0.5,)
        fig.update_layout(yaxis_title="")
        fig.update_layout(xaxis_title="Timeline (by date)")

        return fig, ""
