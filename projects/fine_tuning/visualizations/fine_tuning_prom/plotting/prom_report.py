from dash import html

from . import report
import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

import projects.core.visualizations.helpers.store.prom as core_prom_store

from ..store import prom
from . import report
try:
    from . import error_report
except ImportError:
    error_report = None

def register():
    SutestCpuMemoryReport()
    GpuUsageReport()
    RhoaiFootprintReport()
    ControlPlaneReport()
    LtsReport()


class SutestCpuMemoryReport():
    def __init__(self):
        self.name = "report: Sutest Cluster CPU/Memory Usage"
        self.id_name = self.name.lower().replace("/", "-")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []
        if error_report:
            header += error_report._get_all_tests_setup(args)

        header += [html.P("These plots show an overview of the CPU and Memory usage during the execution of the test, for the cluster, the nodes, and various relevant Pods.")]

        header += ["These plots show the CPU and memory capacity of the SUTest cluster."]
        header += html.Br()
        header += html.Br()

        args_as_timeline = report.set_config(dict(as_timeline=True), args)
        for metric_spec in prom.SUTEST_CONTAINER_LABELS:
            plot_name = list(metric_spec.keys())[0]

            header += [html.H2(plot_name)]
            header += report.Plot_and_Text(f"Prom: {plot_name}: CPU usage", args_as_timeline)
            header += report.Plot_and_Text(f"Prom: {plot_name}: Mem usage", args_as_timeline)


        header += [html.H2("SUTest Cluster")]
        header += report.Plot_and_Text("Prom: sutest cluster memory usage", args_as_timeline)
        header += report.Plot_and_Text("Prom: sutest cluster CPU usage", args_as_timeline)

        return None, header


class GpuUsageReport():
    def __init__(self):
        self.name = "report: GPU Usage"
        self.id_name = self.name.lower().replace("/", "-")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        if error_report:
            header += error_report._get_all_tests_setup(args)

        header += [html.P("These plots show an overview of the GPU usage during the execution of the test")]

        header += [html.H2("GPU Usage")]
        args_as_timeline = report.set_config(dict(as_timeline=True), args)

        for metric_spec in core_prom_store.get_gpu_usage_metrics("sutest", register=False, container="pytorch"):
            plot_name = list(metric_spec.keys())[0]
            header += [html.H3(plot_name)]

            header += report.Plot_and_Text(f"Prom: {plot_name}", args_as_timeline)

        return None, header


class RhoaiFootprintReport():
    def __init__(self):
        self.name = "report: RHOAI Footprint"
        self.id_name = self.name.lower().replace("/", "-")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        if error_report:
            header += error_report._get_all_tests_setup(args)

        header += [html.P("These plots show the CPU and memory footprint of RHOAI operators, by namespaces")]

        header += [html.H2("RHOAI Footprint")]
        args_as_timeline = report.set_config(dict(as_timeline=True), args)

        namespaces = set()
        for metric_spec in prom._get_rhoai_resource_usage("sutest", register=False):
            namespaces.add(list(metric_spec.keys())[0].split()[0])

        for namespace in reversed(sorted(namespaces)):
            header += [html.H3(f"Namespace {namespace}")]
            header += report.Plot_and_Text(f"Prom: Namespace {namespace}: CPU usage", args_as_timeline)
            header += report.Plot_and_Text(f"Prom: Namespace {namespace}: Mem usage", args_as_timeline)

        return None, header



class ControlPlaneReport():
    def __init__(self):
        self.name = "report: Control Plane Nodes Load"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        if error_report:
            header += error_report._get_all_tests_setup(args)

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

            header += report.Plot_and_Text(f"Prom: {cluster_role.title()} Worker Node CPU usage", args)
            header += html.Br()
            header += html.Br()

            header += report.Plot_and_Text(f"Prom: {cluster_role.title()} Worker Node CPU idle", args)
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


class LtsReport():
    def __init__(self):
        self.name = "report: LTS"
        self.id_name = self.name
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, *args):
        header = []
        header += [html.H1("LTS visualization")]

        for stats_name in table_stats.TableStats.stats_by_name.keys():
            if not stats_name.startswith("LTS:"): continue
            header += report.Plot_and_Text(stats_name, args)
            header += html.Br()
            header += html.Br()

        return None, header
