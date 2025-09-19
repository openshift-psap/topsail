import copy
import logging

from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report

def register():
    InitReport()


class InitReport():
    def __init__(self):
        self.name = "report: Init report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.H1("Initialization timing report")]

        header += report.Plot_and_Text(f"SystemD Init timing plot", args)
        header += html.Br()
        header += html.Br()
        header += report.Plot_and_Text(f"OpenShift Init timing plot", args)
        header += html.Br()
        header += html.Br()

        return None, header
