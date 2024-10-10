from dash import html

import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report
import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import error_report

def register():
    PowerReport()

class PowerReport():
    def __init__(self):
        self.name = "report: Power Usage Statistics"
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

        header += html.Br()
        header += [report.Plot("Prom: Power Consumption Per Node (kWh)", args)]
        header += html.Br()
        header += [report.Plot("Prom: Power Consumption for Cluster (kWh)", args)]
        header += html.Br()
        header += [report.Plot("Prom: Power Consumption Total (J)", args)]
        header += html.Br()
        header += [report.Plot("Prom: Power Test", args)]
        header += html.Br()

        return None, header
