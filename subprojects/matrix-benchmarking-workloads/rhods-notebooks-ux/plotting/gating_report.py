import copy

from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common
from . import report

def register():
    GatingReport1()
    GatingReport2()
    GatingReport3()

class GatingReport1():
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

        for entry in common.Matrix.all_records(settings, setting_lists):
            total_users = entry.results.user_count
            success_users = sum(1 for ods_ci in entry.results.ods_ci.values() if ods_ci.exit_code == 0) \
                if entry.results.ods_ci else 0

            txt = f"{success_users}/{total_users} successes"
            if entry.results.from_local_env.source_url:
                txt = html.A(txt, target="_blank", href=entry.results.from_local_env.source_url)
            #header += [html.Ul(html.Li([f"RHODS {entry.settings.version}, {entry.settings.launcher} launcher, run #{entry.settings.run}: ", html.Ul(html.Li(txt))]))]

        header += [html.H2("Gating Test Results (lower is better)")]

        header += report.Plot_and_Text("multi: Notebook Spawn Time", report.set_config(dict(check_all_thresholds=True), args))
        header += ["This plot shows the time it took to spawn a notebook from the user point of view. Lower is better."]
        header += html.Br()

        return None, header

class GatingReport3():
    def __init__(self):
        self.name = "gating report: Performance"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        header += [html.H2("Performance results")]

        for entry in common.Matrix.all_records(settings, setting_lists):
            #header += [html.H3(f"RHODS {entry.settings.version}, {entry.settings.launcher} launcher, run #{entry.settings.run}")]

            header += report.Plot_and_Text("Execution time distribution",
                                           report.set_entry(entry,
                                                            report.set_config(dict(check_all_thresholds=True,
                                                                                   time_to_reach_step="Go to JupyterLab Page"),
                                                                              args)))
        return None, header

class GatingReport2():
    def __init__(self):
        self.name = "gating report: Notebook Performance"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []
        header += [html.H2("Functional Test Results")]

        for entry in common.Matrix.all_records(settings, setting_lists):
            txt = f"results"
            if entry.results.from_local_env.source_url:
                txt = html.A(txt, target="_blank", href=entry.results.from_local_env.source_url)
            header += [html.Ul(html.Li([f" {entry.settings.instance_type} machine: ", html.Ul(html.Li(txt))]))]

        header += [html.H2("Gating Test Results (lower is better)")]

        header += [html.H3("Python Performance")]
        header += report.Plot_and_Text("Notebook Python Performance Comparison",
                                       report.set_config(dict(check_all_thresholds=True), args))
        header += ["This plot shows a Python compute performance indicator comparison. Lower is better."]
        header += html.Br()

        return None, header
