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
        if sum(1 for _ in common.Matrix.all_records(settings, setting_lists)) != 1:
            return {}, "ERROR: only one experiment must be selected"

        for entry in common.Matrix.all_records(settings, setting_lists):
            pass

        header = []

        header += [html.P("This report shows the RHODS/Notebook performance testing setup and results.")]
        header += [html.H1("Performance Report")]

        setup_info = error_report._get_test_setup(entry)
        header += [html.Ul(
            setup_info
        )]

        header += [html.H2("Execution time distribution for getting a usable Notebook")]

        msg_p = []
        header += [report.Plot("Execution time distribution",
                        report.set_config(dict(time_to_reach_step="Go to JupyterLab Page"), args),
                        msg_p,
                        )]
        header += [html.I(msg_p[0]), html.Br()]

        header += [f"This plot is important to understand the time it took for the {entry.results.user_count} users to reach JupyterLab."]
        header += [html.Br()]
        header += [html.Br()]

        msg_p = []
        header += [html.H2("Start time distribution")]
        header += [report.Plot("Launch time distribution", args, msg_p,)]
        header += [html.I(msg_p[0]), html.Br()]

        start_delay = float(entry.results.tester_job.env["SLEEP_FACTOR"])
        total_delay = start_delay * entry.results.user_count

        header += [f"This plot is important to understand how ", html.I("simultaneous"), " the execution of the users was.",
                   html.Br(),
                   f"The duration of the first steps reflect the startup delay enforced by the test framework ",
                   html.Br(),
                   f"The startup delay is configured to {start_delay:.1f} seconds between each user, or a total of {total_delay:.0f} seconds ({total_delay/60:.1f} minutes) between the first and last user joining the test."]
        header += [html.Br()]
        header += [html.Br()]

        return None, header
