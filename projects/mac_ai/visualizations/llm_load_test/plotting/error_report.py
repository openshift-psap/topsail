import copy
import re
from collections import defaultdict
import os
import base64
import pathlib
import yaml

from dash import html
from dash import dcc

from matrix_benchmarking.common import Matrix
import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report


def register():
    ErrorReport()


def _get_test_setup(entry):
    setup_info = []

    artifacts_basedir = entry.results.from_local_env.artifacts_basedir

    setup_info += [html.Li([
        "Test UUID: ",
        html.Code(f"- {entry.results.test_uuid}\n", style={"white-space": "pre-wrap"}),
    ])]

    setup_info += [html.Li([
        "Test variables: ",
        html.Code(yaml.dump([entry.settings.__dict__]), style={"white-space": "pre-wrap"}),
    ])]


    setup_info += [html.Li([
        "Model configuration: ",
        html.Code(yaml.dump([entry.results.test_config.get("test.model")]), style={"white-space": "pre-wrap"}),
    ])]

    setup_info += [html.Li([
        "Llm-load-test configuration: ",
        html.Code(yaml.dump([entry.results.test_config.get("test.llm_load_test.args")]), style={"white-space": "pre-wrap"}),
    ])]

    if artifacts_basedir:
        setup_info += [html.Li(html.A("Results artifacts", href=str(artifacts_basedir), target="_blank"))]

    else:
        setup_info += [html.Li(f"Results artifacts: NOT AVAILABLE ({entry.results.from_local_env.source_url})")]

    return setup_info


def simplify_error(error):
    if not error:
        return error

    if "CUDA out of memory" in error:
        return "CUDA out of memory"

    if (partition := error.partition("read tcp"))[1]:
        simplify = partition[0]
        simplify += "read tcp: "
        simplify += partition[2].partition(": ")[2]

        if "use of closed network connection" in simplify:
            # not an error
            return None

        return simplify

    return error


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

        for entry in common.Matrix.all_records(settings, setting_lists):
            name = (" of "+entry.get_name(variables)) if variables else ""
            header += [html.H1(f"Error Report{name}")]

            header += [html.Ul(
                _get_test_setup(entry)
            )]

        return None, header
