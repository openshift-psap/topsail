import copy
import re
from collections import defaultdict
import os
import base64

from dash import html
from dash import dcc

from matrix_benchmarking.common import Matrix
import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common
import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report

from . import error_report
from . import prom_report

def register():
    PerfReport()

class PerfReport():
    def __init__(self):
        self.name = "report: Performance report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        cnt = common.Matrix.count_records(settings, setting_lists)

        if cnt != 1:
            return {}, "ERROR: only one experiment must be selected"

        entry = None
        for entry in common.Matrix.all_records(settings, setting_lists):
            pass

        header = []

        header += [html.P("This report shows the RHODS/Notebook performance testing setup and results.")]
        header += [html.H1("Performance Report")]

        if entry:
            setup_info = error_report._get_test_setup(entry)
            header += [html.Ul(
                setup_info
            )]

        header += [html.H2("Median Runtime Timeline")]
        header += report.Plot_and_Text(f"Median runtime timeline", args)
        header += ["This plot shows the timeline for the execution of each of the step.", html.Br(),
                   "The main bar show the media time, and the error bars show the Q1-Q3 distance.", html.Br(),
                   "This range includes 50% of the users. ", html.Br(),
                   "Only the users who succeeded the step are included in the computation.", html.Br()]

        header += [html.Br()]
        header += [html.Br()]

        header += [html.H2("Control plane nodes health")]

        header += report.Plot_and_Text(f"Prom: Sutest API Server Requests (server errors)", args)
        header += html.Br()
        header += html.Br()
        header += ["This plot shows the number of APIServer errors (5xx HTTP codes). Lower is better."]

        header += report.Plot_and_Text(f"Prom: Sutest Control Plane Node CPU idle", args)
        header += html.Br()
        header += html.Br()
        header += ["This plot shows the idle time of the control plane nodes. Higher is better."]

        return None, header
