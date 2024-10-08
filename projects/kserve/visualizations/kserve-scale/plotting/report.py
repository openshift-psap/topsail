import copy
import logging

from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

try:
    from . import error_report
except ImportError:
    error_report = None


def register():
    UserProgressReport()
    UserProgressDetailsReport()


class UserProgressReport():
    def __init__(self):
        self.name = "report: User Progress"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []

        header += error_report._get_all_tests_setup(args)

        header += [html.H1("User Progress")]

        header += [report.Plot(f"User progress", args)]
        header += [report.Plot(f"User progress", report.set_config(dict(hide_launch_delay=False), args))]

        header += report.Plot_and_Text(f"Resource Creation Delay", report.set_config(dict(as_distribution=True), args))

        header += [html.H1("GRPC calls distribution")]
        header += report.Plot_and_Text(f"GRPC calls distribution", report.set_config(dict(show_attempts=False), args))
        header += report.Plot_and_Text(f"GRPC calls distribution", report.set_config(dict(show_attempts=True), args))

        header += [html.H1("Resource Creation")]

        header += report.Plot_and_Text(f"Inference Services Progress", args)

        header += report.Plot_and_Text(f"Interval Between Creations", args)

        header += report.Plot_and_Text(f"Resource Creation Timeline", args)

        header += report.Plot_and_Text(f"Resource Creation Delay", report.set_config(dict(model_id=None), args))

        header += [html.H1("Resource Conditions")]

        for kind in ("InferenceService", "Revision"):
            header += report.Plot_and_Text(f"Conditions Timeline", report.set_config(dict(kind=kind), args))

            header += report.Plot_and_Text(f"Conditions in State Timeline", report.set_config(dict(kind=kind), args))

        return None, header


class UserProgressDetailsReport():
    def __init__(self):
        self.name = "report: User Progress Details"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []

        header += error_report._get_all_tests_setup(args)

        header += [html.H1("Resource Creation")]

        ordered_vars, settings, setting_lists, variables, cfg = args
        for entry in common.Matrix.all_records(settings, setting_lists):
            models_per_ns = entry.results.test_config.get("tests.scale.model.replicas")
            for model_id in range(models_per_ns):
                header += report.Plot_and_Text(f"Resource Creation Delay", report.set_config(dict(model_id=model_id), args))

        return None, header
