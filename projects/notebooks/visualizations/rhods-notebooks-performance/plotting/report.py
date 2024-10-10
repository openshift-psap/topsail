import copy
import logging

from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    NotebookPerformanceReport()


class NotebookPerformanceReport():
    def __init__(self):
        self.name = "report: Notebook Performance"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []
        header += [html.H2("Notebook Performance")]

        for entry in common.Matrix.all_records(settings, setting_lists):
            if ordered_vars:
                header.append(html.H3(", ".join(f"{k}={entry.settings.__dict__[k]}" for k in ordered_vars)))

            header += report.Plot_and_Text("Notebook Performance",
                                    report.set_config(dict(user_details=1, stacked=1),
                                                      report.set_entry(entry, args)))

            header += ["This plot shows the distribution of the notebook performance benchmark results, "
                       "when a single notebook is running on the node."]

            header += html.Br()
            header += html.Br()

        return None, header
