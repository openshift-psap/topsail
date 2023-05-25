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

from . import report
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

        header += [html.H2("Notebook Spawn Time")]

        msg_p = []
        header += [report.Plot("Execution time distribution",
                        report.set_config(dict(time_to_reach_step="Go to JupyterLab Page"), args),
                        msg_p,
                        )]
        header += [html.I(msg_p[0]), html.Br()]

        header += ["This plot shows the time it took to spawn a notebook from the user point of view. Lower is better."]

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

        prom_report.add_pod_cpu_mem_usage(header, "RHODS Dashboard", args, cpu_only=True)

        return None, header
