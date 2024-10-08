import copy
import logging

from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    ControlPlaneReport()
    WorkerNodesReport()
    ResourceAllocationReport()
    TimeInStateDistributionReport()


class ControlPlaneReport():
    def __init__(self):
        self.name = "report: Control Plane Nodes Load"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.H1("Control Plane Nodes Load")]

        for cluster_role in ["sutest"]:
            header += [html.H1(f"{cluster_role.title()} cluster")]

            header += ["These plots shows the CPU and memory usage of the Kubernetes API Server and ETCD, running on the Control Plane nodes of the cluster."]

            for pod_name in ["ApiServer", "ETCD"]:
                header += [html.H2(f"{pod_name} subsystem")]

                for what in ["CPU", "Mem"]:
                    header += report.Plot_and_Text(f"Prom: {cluster_role.title()} {pod_name}: {what} usage", args)
                    header += html.Br()
                    header += html.Br()

            if cluster_role != "sutest": continue

            header += [html.H2(f"CPU usage")]

            header += ["These plots shows the CPU usage of the Control Plane nodes.",
                       html.Br(),
                       "The first plot show all the available modes, while the second one shows only the idle time (higher is better).",
                       html.Br(),
                       "The Y scale is arbitrary, but for a given node, the sum of all the modes at a given time indicate 100% of the CPU."
                       ]

            header += report.Plot_and_Text(f"Prom: {cluster_role.title()} Control Plane Node CPU usage", args)
            header += html.Br()
            header += html.Br()

            header += report.Plot_and_Text(f"Prom: {cluster_role.title()} Control Plane Node CPU idle", args)
            header += html.Br()
            header += html.Br()

            header += [html.H2(f"APIServer requests duration")]
            for verb in ["LIST", "GET", "PUT", "PATCH"]:
                header += report.Plot_and_Text(f"Prom: {cluster_role.title()} API Server {verb} Requests duration", args)
                header += html.Br()
                header += html.Br()

            header += [html.H2(f"API Server HTTP return codes")]
            for what in ["successes", "client errors", "server errors"]:
                header += report.Plot_and_Text(f"Prom: {cluster_role.title()} API Server Requests ({what})", args)
                header += html.Br()
                header += html.Br()

        return None, header


class WorkerNodesReport():
    def __init__(self):
        self.name = "report: Worker Nodes Load"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.H1("Worker Nodes Load")]

        header += report.Plot_and_Text(f"Prom: Sutest Worker Node CPU usage", args)
        header += html.Br()
        header += html.Br()

        header += report.Plot_and_Text(f"Prom: Sutest Worker Node CPU idle", args)
        header += html.Br()
        header += html.Br()

        header += [html.H1("Node Resource Allocation")]

        header += ["These plots shows the CPU, memory and GPU allocation in the worker nodes of the cluster."]

        ordered_vars, settings, setting_lists, variables, cfg = args

        for entry in common.Matrix.all_records(settings, setting_lists):
            break

        for node_name in sorted(entry.results.nodes_info):
            node = entry.results.nodes_info[node_name]
            if node.control_plane: continue
            header += [html.H1(f"Node {node.name}")]

            for what in "cpu", "memory", "gpu":

                if what == "gpu" and node.allocatable.gpu == 0:
                    header += [html.P("No GPU on this node."), html.Br()]
                    continue

                header += report.Plot_and_Text(f"Node Resource Allocation", report.set_config(dict(what=what, instance=node.name), args))
                header += html.Br()
                header += html.Br()

        return None, header


class ResourceAllocationReport():
    def __init__(self):
        self.name = "report: Resource Allocation Timelines"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args
        cnt = common.Matrix.count_records(settings, setting_lists)
        if cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {cnt}."

        header = []

        header += [html.H1("Resources Timelines")]

        header += report.Plot_and_Text(f"AppWrappers Timeline", args)

        header += report.Plot_and_Text(f"AppWrappers in State Timeline", args)

        header += report.Plot_and_Text(f"Resource Mapping Timeline", args)

        return None, header


class TimeInStateDistributionReport():
    def __init__(self):
        self.name = "report: Time in AppWrapper State Distribution"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):

        header = []
        header += [html.P("These plots show the distribution of time spent in the different AppWrappers states.")]

        header += [html.H2("Overview of the Execution time distribution")]
        header += report.Plot_and_Text("Execution time distribution", args)
        header += [html.Br()]
        header += [html.Br()]

        header += ["The plots below show the break down of the execution timelength for the different steps."]

        ordered_vars, settings, setting_lists, variables, cfg = args

        if not common.Matrix.has_records(settings, setting_lists):
            return None, "No experiments available"

        header += [html.H2("Time in state for each of the states")]

        for entry in common.Matrix.all_records(settings, setting_lists):
            break

        state_names = [] # set() do not preserve the order
        for resource_name, resource_times in entry.results.resource_times.items():
            if resource_times.kind != "AppWrapper": continue
            for condition_name, condition_ts in resource_times.aw_conditions.items():
                if condition_name not in state_names:
                    state_names.append(condition_name)

        for state_name in state_names:
            header += report.Plot_and_Text("Execution time distribution",
                                           report.set_config(dict(state=state_name), args))

        return None, header
