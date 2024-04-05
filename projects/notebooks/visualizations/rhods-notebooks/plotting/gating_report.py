import copy

from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common
from . import report

def register():
    GatingReportFunctionalSpawn()
    GatingReportHealthCheck()

class GatingReportFunctionalSpawn():
    def __init__(self):
        self.name = "gating report: Functional and Spawn Time"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []
        header += [html.H2("Functional Test Results")]

        # User successes
        header += [html.H2("User successes")]
        header += report.Plot_and_Text("Step successes",
                                       report.set_config(dict(all_in_one=True, check_all_thresholds=True), args))
        header += ["This plot shows the number of users who passed and failed each of the tests."]
        header += html.Br()

        # Notebook Spawn Time
        header += [html.H2("Notebook Spawn Time")]
        header += report.Plot_and_Text("multi: Notebook Spawn Time",
                                       report.set_config(dict(check_all_thresholds=True), args))
        header += ["This plot shows the time it took to spawn a notebook from the user point of view. Lower is better."]
        header += html.Br()

        return None, header

class GatingReportHealthCheck():
    def __init__(self):
        self.name = "gating report: Health Check"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args
        header = []

        # Control_Plane nodes health
        header += [html.H2("Control Plane nodes health")]
        header += report.Plot_and_Text("Prom: Sutest API Server Requests (server errors)",
                                       report.set_config(dict(check_all_thresholds=True), args))
        header += ["This plot shows the number of APIServer errors (5xx HTTP codes). Lower is better."]
        header += html.Br()

        header += report.Plot_and_Text("Prom: Sutest Control Plane Node CPU idle",
                                       report.set_config(dict(check_all_thresholds=True), args))
        header += ["This plot shows the idle time of the control plane nodes. Higher is better."]
        header += html.Br()

        return None, header
