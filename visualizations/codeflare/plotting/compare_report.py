from dash import html

from . import report
import matrix_benchmarking.plotting.table_stats as table_stats

def register():
    CompareSpeedReport()


class CompareSpeedReport():
    def __init__(self):
        self.name = "report: Speed Comparison"
        self.id_name = self.name.lower().replace("/", "-")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []


        header += [html.P("These plots show the comparison of the processing speed of MCAD for different test configurations.")]

        header += [html.H2("Processing Speed Comparison")]

        header += report.Plot_and_Text("Compare Test Speed", args)

        return None, header
