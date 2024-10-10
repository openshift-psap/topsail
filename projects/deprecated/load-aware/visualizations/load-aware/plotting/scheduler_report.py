import copy
import logging

from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import error_report

def register():
    SchedulerReport()
    NodeUtilisationReport()


class SchedulerReport():
    def __init__(self):
        self.name = "report: scheduler performance"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []

        ordered_vars, settings, setting_lists, variables, cfg = args
        for entry in common.Matrix.all_records(settings, setting_lists):
            header += error_report._get_test_setup(entry)
            header += [html.Hr()]

        header += [html.H1("Performance of Load-Aware Scheduling")]
        header += ["Performance metrics to evaluate load-aware scheduling"]

        header += [html.H1(f"Pod time distribution")]

        for workload in ["make", "sleep"]:
            header += [html.H2(f"{workload} workload pods")]
            header += report.Plot_and_Text("Pod time distribution", report.set_config(dict(workload=workload), args))
            header += html.Br()
            header += html.Br()

        header += [html.H1(f"Pod execution timeline")]
        header += report.Plot_and_Text("Pod execution timeline", args)
        header += html.Br()
        header += html.Br()

        header += [html.H1(f"Resource Mapping Timeline")]

        header += report.Plot_and_Text("Resource Mapping Timeline", args)
        header += html.Br()
        header += html.Br()

        for workload in ["make", "sleep"]:
            header += [html.H3(f"Timeline of the '{workload}' Pods")]
            header += report.Plot_and_Text("Resource Mapping Timeline", report.set_config(dict(workload=workload), args))
            header += html.Br()
            header += html.Br()

        return None, header


class NodeUtilisationReport():
    def __init__(self):
        self.name = "report: Node Utilisation"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []

        ordered_vars, settings, setting_lists, variables, cfg = args
        for entry in common.Matrix.all_records(settings, setting_lists):
            header += error_report._get_test_setup(entry)

        header += [html.H1(f"Pod/Node distribution")]

        for workload in [False, "make", "sleep"]:
            header += report.Plot_and_Text("Pod/Node distribution", report.set_config(dict(workload=workload), args))

        header += [html.H1(f"Pod/Node utilisation")]

        for node in entry.results.cluster_info.workload:
            header += [html.H3(f"All the pods on {node.name}")]
            header += report.Plot_and_Text("Resource Mapping Timeline", report.set_config(dict(instance=node.name), args))

        header += [html.H1(f"Make Node utilisation")]

        for node in entry.results.cluster_info.workload:
            header += [html.H3(f"Make pods on {node.name}")]
            header += report.Plot_and_Text("Resource Mapping Timeline", report.set_config(dict(workload="make", instance=node.name), args))

        return None, header
