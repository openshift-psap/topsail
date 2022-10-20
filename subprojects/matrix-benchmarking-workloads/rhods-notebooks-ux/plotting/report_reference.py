from dash import html

from . import report
import matrix_benchmarking.plotting.table_stats as table_stats

def register():
    ReferenceReport()


class ReferenceReport():
    def __init__(self):
        self.name = "report: Reference comparisons"
        self.id_name = self.name.lower().replace("/", "-")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.P("These plots show a comparison between multiple reference runs.")]


        header += [html.H2("User successes")]
        header += report.Plot_and_Text("Step successes", report.set_config(dict(all_in_one=True), args))

        header += ["This plot shows the number of users who passed and failed each of the tests."]
        header += html.Br()

        header += [html.H2("Notebook Spawn Time")]
        header += report.Plot_and_Text("multi: Notebook Spawn Time", args)

        header += ["This plot shows the time it took to spawn a notebook from the user point of view. Lower is better."]
        header += html.Br()

        header += [html.H2("Master nodes health")]

        header += report.Plot_and_Text("Prom: Sutest API Server Requests (server errors)", args)
        header += ["This plot shows the number of APIServer errors (5xx HTTP codes). Lower is better."]
        header += html.Br()

        header += report.Plot_and_Text("Prom: Sutest Master Node CPU idle", args)
        header += ["This plot shows the idle time of the master nodes. Higher is better."]
        header += html.Br()



        header += [html.H2("Dashboard health")]

        header += report.Plot_and_Text("Prom: RHODS Dashboard: CPU usage", args)
        header += ["This plot shows the CPU usage of the Dashboard pods. Lower is better."]
        header += html.Br()

        return None, header
