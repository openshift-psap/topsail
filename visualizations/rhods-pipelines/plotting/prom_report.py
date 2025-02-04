from dash import html

import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report
import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common
from ..store import prom

def register():
    DSPACpuMemoryReport()
    SutestCpuMemoryReport()
    DriverCpuMemoryReport()

class DSPACpuMemoryReport():
    def __init__(self):
        self.name = "report: DSPA CPU/Memory Usage"
        self.id_name = self.name.lower().replace("/", "-")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        header += [html.P("These plots show an overview of the CPU and Memory usage during the execution of the test, for the cluster, the nodes, and various relevant Pods.")]

        header += ["These plots show the CPU and memory capacity of the DSPA pods"]
        header += html.Br()
        header += html.Br()

        args_as_timeline = report.set_config(dict(as_timeline=True), args)
        for metric_spec in prom.DSPA_CONTAINER_LABELS:
            plot_name = list(metric_spec.keys())[0]
            header += [html.H2(plot_name)]
            header += report.Plot_and_Text(f"Prom: {plot_name}: CPU usage", args_as_timeline)
            header += report.Plot_and_Text(f"Prom: {plot_name}: Mem usage", args_as_timeline)

        return None, header

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


class DriverCpuMemoryReport():
    def __init__(self):
        self.name = "report: Driver Cluster CPU/Memory Usage"
        self.id_name = self.name.lower().replace("/", "-")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        header += [html.P("These plots show an overview of the CPU and Memory usage during the execution of the test, for the cluster, the nodes, and various relevant Pods.")]

        header += ["These plots show the CPU and memory capacity of the Driver cluster."]
        header += html.Br()
        header += html.Br()

        args_as_timeline = report.set_config(dict(as_timeline=True), args)
        for metric_spec in prom.DRIVER_CONTAINER_LABELS:
            plot_name = list(metric_spec.keys())[0]

            header += [html.H2(plot_name)]
            header += report.Plot_and_Text(f"Prom: {plot_name}: CPU usage", args_as_timeline)
            header += report.Plot_and_Text(f"Prom: {plot_name}: Mem usage", args_as_timeline)


        header += [html.H2("Driver Cluster")]
        header += report.Plot_and_Text("Prom: driver cluster memory usage", args_as_timeline)
        header += report.Plot_and_Text("Prom: driver cluster CPU usage", args_as_timeline)

        return None, header
