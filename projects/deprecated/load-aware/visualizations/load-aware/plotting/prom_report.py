from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report

def register():
    SutestCpuMemoryReport()


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

        ordered_vars, settings, setting_lists, variables, cfg = args
        for entry in common.Matrix.all_records(settings, setting_lists):
            header += error_report._get_test_setup(entry)
            header += [html.Hr()]

        header += [html.P("These plots show an overview of the CPU and Memory usage during the execution of the test, for the cluster, the nodes, and various relevant Pods.")]

        header += [html.H2("SUTest Cluster")]
        header += [report.Plot("Prom: sutest cluster memory usage", args)]
        header += [report.Plot("Prom: sutest cluster CPU usage", args)]

        header += ["These plots show the CPU and memory capacity of the SUTest cluster."]
        header += html.Br()
        header += html.Br()

        header += [html.H2("SUTest Nodes")]

        header += [report.Plot("Prom: Sutest Node CPU Utilisation rate", args)]

        header += ["These plots show the CPU utilisation rate (over 1 minute) of the SUTest nodes, with the metrics used by Trimaran."]
        header += html.Br()
        header += html.Br()

        return None, header
