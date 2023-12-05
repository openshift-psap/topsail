from dash import html

from . import report
import matrix_benchmarking.plotting.table_stats as table_stats

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

def add_pod_cpu_mem_usage(header, what, args, mem_only=False, cpu_only=False):
    if mem_only:
        header += [html.H2(f"{what} Memory usage")]
        descr = "memory"
        these_plots_show = "This plot shows"
    elif cpu_only:
        header += [html.H2(f"{what} CPU usage")]
        descr = "CPU"
        these_plots_show = "This plot shows"
    else:
        header += [html.H2(f"{what} CPU and Memory usage")]
        descr = "CPU and memory"
        these_plots_show = "These plots show"

    if not cpu_only:
        header += [report.Plot(f"Prom: {what}: Mem usage", args)]
    if not mem_only:
        header += [report.Plot(f"Prom: {what}: CPU usage", args)]

    header += [f"{these_plots_show} the {descr} usage of {what} Pods. "]
    header += ["The ", html.Code("requests"), " and ", html.Code("limits"),
                   " values are shown with a dashed line, ", html.I("if they are defined"), " in the Pod spec."]
    header += html.Br()
    header += html.Br()


class SutestCpuMemoryReport():
    def __init__(self):
        self.name = "report: Sutest Cluster CPU/Memory Usage"
        self.id_name = self.name.lower().replace("/", "-")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
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
            header += [report.Plot(f"Prom: {plot_name}: CPU usage", args_as_timeline)]
            header += [report.Plot(f"Prom: {plot_name}: Mem usage", args_as_timeline)]


        header += [html.H2("SUTest Cluster")]
        header += [report.Plot("Prom: sutest cluster memory usage", args_as_timeline)]
        header += [report.Plot("Prom: sutest cluster CPU usage", args_as_timeline)]

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

        for metric_spec in prom._get_gpu_usage("sutest", register=False):
            plot_name = list(metric_spec.keys())[0]
            header += [html.H3(plot_name)]

            header += [report.Plot(f"Prom: {plot_name}", args_as_timeline)]

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
            header += [report.Plot(f"Prom: Namespace {namespace}: CPU usage", args_as_timeline)]
            header += [report.Plot(f"Prom: Namespace {namespace}: Mem usage", args_as_timeline)]

        return None, header
