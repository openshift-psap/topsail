from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import report
from . import error_report
from ..store import prom as prom_store

def register():
    SutestCpuMemoryReport()
    PromSchedulingReport()

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
        for metric_spec in prom_store.SUTEST_CONTAINER_LABELS:
            plot_name = list(metric_spec.keys())[0]

            header += [html.H2(plot_name)]
            header += report.Plot_and_Text(f"Prom: {plot_name}: CPU usage", args_as_timeline)
            header += report.Plot_and_Text(f"Prom: {plot_name}: Mem usage", args_as_timeline)

        header += [html.H2("SUTest Cluster")]
        header += report.Plot_and_Text("Prom: sutest cluster memory usage", args_as_timeline)
        header += report.Plot_and_Text("Prom: sutest cluster CPU usage", args_as_timeline)

        return None, header


class PromSchedulingReport():
    def __init__(self):
        self.name = "report: Prometheus Scheduling"
        self.id_name = self.name.lower().replace("/", "-")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []

        header += [html.P("These plots show an overview of the scheduling, from Prometheus metrics")]

        header += [html.H2("Scheduling")]
        args_as_timeline = report.set_config(dict(as_timeline=True), args)

        for metric_spec in prom_store.get_scheduling_metrics("sutest", register=False):
            plot_name = list(metric_spec.keys())[0]

            if "Batch Job" in plot_name: continue

            header += [html.H3(plot_name)]

            header += report.Plot_and_Text(f"Prom: {plot_name}", args_as_timeline)

        header += [html.H3("Batch Jobs Status")]
        header += report.Plot_and_Text(f"Prom: Batch Jobs Status", args_as_timeline)

        header += [html.H2("SUTest Cluster")]
        header += report.Plot_and_Text("Prom: sutest cluster memory usage", args_as_timeline)
        header += report.Plot_and_Text("Prom: sutest cluster CPU usage", args_as_timeline)

        return None, header
