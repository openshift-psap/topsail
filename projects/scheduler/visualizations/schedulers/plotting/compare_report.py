from dash import html

import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report
import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

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
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        header += [html.P("These plots show the comparison of the processing speed of MCAD for different test configurations.")]

        header += [html.H2("Processing Speed Comparison")]

        header += report.Plot_and_Text("Compare Test Speed", args)

        header += ["The plot above shows the time it took for the MCAD scale test to run, divided by the number of Pods/AppWrappers that had to be created (giving a processing speed, in Pods per minutes). Higher is better)"]
        if "mcad" in common.Matrix.settings["mode"]:
            header += [html.Br()]
            header += ["The ", html.I("Launch speed"), "  is the speed at which the resources are created in the ETCD database."]

        header += [html.Br()]
        header += ["The ", html.I("Processing speed"), " is the speed at which the test completed, including the Pod execution time (if any)."]
        header += [html.Br()]
        header += ["The ", html.I("Speed to last schedule"), " is the speed at which the test executed, excluding the last Pod execution (if any)."]

        if "mcad" in common.Matrix.settings["mode"]:
            header += report.Plot_and_Text("Compare Launch Speed", args)

            header += ["The plot above shows the number of resources (AppWrappers or Jobs) actually created in the ETCD database, plotted against the time since the beginning of the test. It helps understanding if the resources were created at a normal pace, or, if there are unexpected detays during the creation phase."]

        if "mcad" in common.Matrix.settings["mode"]:
            header += report.Plot_and_Text("Compare Cleanup Speed", args)
            header += ["The plot above shows the number of AppWrappers deleted per seconds.", html.B("This is a _tentative_ to show the cleanup duration (based on the processing of a canary AppWrapper)."), "The actual progress of the clean up is hard to track without MCAD-internal metrics."]

        return None, header
