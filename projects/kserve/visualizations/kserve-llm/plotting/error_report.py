import copy
import re
from collections import defaultdict
import os
import base64
import pathlib

from dash import html
from dash import dcc

from matrix_benchmarking.common import Matrix
import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import report

def register():
    ErrorReport()


def _get_test_setup(entry):
    setup_info = []

    artifacts_basedir = entry.results.from_local_env.artifacts_basedir
    setup_info += ["Test settings", html.Code(" ".join([f"{k}={v}" for k,v in entry.settings.__dict__.items()]))]
    if artifacts_basedir:
        setup_info += [html.Li(html.A("Results artifacts", href=str(artifacts_basedir), target="_blank"))]

    else:
        setup_info += [html.Li(f"Results artifacts: NOT AVAILABLE ({entry.results.from_local_env.source_url})")]

    return setup_info


def simplify_error(error):
    if (partition := error.partition("read tcp"))[1]:
        simplify = partition[0]
        simplify += "read tcp: "
        simplify += partition[2].partition(": ")[2]

        if "use of closed network connection" in simplify:
            # not an error
            return None

        return simplify

    return error


def _get_test_details(entry, args):
    header = []

    header += [html.H2("Error distribution")]

    llm_data = entry.results.llm_load_test_output

    errorDistribution = defaultdict(int)
    success_count = 0
    for idx, block in enumerate(llm_data):
        error_count = 0
        for descr, count in block.get("errorDistribution", {}).items():
            simplified_error = simplify_error(descr)
            if not simplified_error:
                continue

            errorDistribution[simplified_error] += count
            error_count += count
        success_count += len(block["details"]) - error_count
    errorDistribution["success"] = success_count

    header += report.Plot_and_Text(f"Latency details", report.set_config(dict(show_errors=True, entry=entry), args))
    header += [html.I("Click on the graph to see the error labels in the interactive view.")]
    header += [html.Br(), html.Br()]
    header += ["Number of successful calls and error count:"]
    errors = []

    for descr, count in sorted(errorDistribution.items()):
        errors += [html.Li([html.Code(descr), " 🠊 ", f"{count} call{'s' if count > 1 else ''}"])]
    header += [html.Ul(errors)]

    return header


def _get_error_overview(entries, args):
    ordered_vars, settings, setting_lists, variables, cfg = args

    header = []
    header += [html.H2("Error overview")]

    errorDistribution = defaultdict(int)
    for entry in entries:
        llm_data = entry.results.llm_load_test_output
        success_count = 0
        for idx, block in enumerate(llm_data):
            error_count = 0
            for descr, count in block.get("errorDistribution", {}).items():
                simplified_error = simplify_error(descr)
                if not simplified_error:
                    continue

                errorDistribution[simplified_error] += count
                error_count += count
            success_count += len(block["details"]) - error_count
        errorDistribution[entry.get_name(variables)] = success_count

    graph_text = report.Plot_and_Text(f"Errors distribution", args)

    if graph_text[0] and graph_text[0].figure:
        header += graph_text
        header += [html.I("Click on the graph to see the error labels in the interactive view.")]

    graph_text = report.Plot_and_Text(f"Latency details", report.set_config(dict(only_errors=True), args))
    if graph_text[0] and graph_text[0].figure:
        header += graph_text
        header += [html.I("Click on the graph to see the error labels in the interactive view.")]
        header += [html.Br(), html.Br()]

    header += report.Plot_and_Text(f"Success count distribution", args)
    header += ["Number of successful requests and error count, for each of the tests:"]

    errors = []
    for descr, count in sorted(errorDistribution.items()):
        errors += [html.Li([html.Code(descr), " 🠊 ", f"{count} call{'s' if count > 1 else ''}"])]
    header += [html.Ul(errors)]

    header += [html.H2("Load time")]
    header += report.Plot_and_Text(f"Load time", report.set_config(dict(init_time=True), args))
    header += report.Plot_and_Text(f"Load time", report.set_config(dict(init_time=False), args))
    header += [html.I("The plots above shows the initialization and load duration of the model")]

    header += [html.H2("Log stats")]
    header += report.Plot_and_Text(f"Log distribution", report.set_config(dict(line_count=True), args))
    header += [html.I("The plot above shows the number of log lines collected for the Predicator Pod(s). Too many lines may increase the response time. Mind that the Pods are not restarted between all of the tests.")]

    header += report.Plot_and_Text(f"Log distribution", report.set_config(dict(line_count=False), args))
    header += [html.I("The plot above shows the occurence count of various well-known log lines. Too many of them (thousands) might be the sign of runtime issues.")]

    return header


class ErrorReport():
    def __init__(self):
        self.name = "report: Error report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        header = []

        args = ordered_vars, settings, setting_lists, variables, cfg
        if common.Matrix.count_records(settings, setting_lists) != 1:
            header += _get_error_overview(common.Matrix.all_records(settings, setting_lists), args)

        for entry in common.Matrix.all_records(settings, setting_lists):
            name = (" of "+entry.get_name(variables)) if variables else ""
            header += [html.H1(f"Error Report{name}")]

            header += [html.Ul(
                _get_test_setup(entry)
            )]

            header += _get_test_details(entry, args)

        return None, header
