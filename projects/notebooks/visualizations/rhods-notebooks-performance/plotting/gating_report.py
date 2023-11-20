from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common
from . import report

def register():
    GatingReport()

class GatingReport():
    def __init__(self):
        self.name = "gating report: Notebook Performance"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        header += [html.H2("Gating Test Results (lower is better)")]

        header += [html.H3("Python Performance")]
        header += report.Plot_and_Text("Notebook Python Performance Comparison",
                                       report.set_config(dict(check_all_thresholds=False), args))
        header += ["This plot shows a Python compute performance indicator comparison. Lower is better."]
        header += html.Br()

        header += [html.H2("Functional Test Results")]

        for entry in common.Matrix.all_records(settings, setting_lists):
            txt = f"results"
            if entry.results.from_local_env.source_url:
                txt = html.A(txt, target="_blank", href=entry.results.from_local_env.source_url)
            if hasattr(entry.settings, "image"):
                header += [html.Ul(html.Li([f" {entry.settings.image} image: ", html.Ul(html.Li(txt))]))]

        return None, header
