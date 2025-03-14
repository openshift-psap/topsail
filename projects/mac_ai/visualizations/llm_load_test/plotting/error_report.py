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
        "Test UUID",
        html.Code(f"- {entry.results.test_uuid}\n", style={"white-space": "pre-wrap"}),
    ])]

    setup_info += [html.Li([
        "Test variables",
        html.Code(yaml.dump([entry.settings.__dict__]), style={"white-space": "pre-wrap"}),
    ])]


    inference_server_cfg = dict()
    inference_server_cfg["platform"] = entry.results.test_config.get("test.platform")
    inference_server_cfg["engine"] = entry.results.test_config.get("test.inference_server.name")
    inference_server_cfg["version"] = entry.results.test_config.get("prepare.llama_cpp.repo.version")
    inference_server_links = []

    inference_server_info = [
        "Inference server",
    ]

    inference_server_links += [html.Li(["configuration", html.Code(yaml.dump([inference_server_cfg]).strip(), style={"white-space": "pre-wrap"})])]
    if artifacts_basedir:
        if entry.results.file_links and entry.results.file_links.server_logs:
            inference_server_links += [html.Li([html.A("execution logs", href=artifacts_basedir /entry.results.file_links.server_logs, target="_blank")])]
        else:
            inference_server_links += [html.Li(["execution logs not available :/"])]

        if entry.results.file_links and entry.results.file_links.server_build_logs:
            inference_server_links += [html.Li(
                ["build logs:",
                 html.Ul(
                     [html.Li(html.A(name, href=artifacts_basedir / log_file, target="_blank")) for name, log_file in entry.results.file_links.server_build_logs.items()]
                 )
                ]
            )]
        else:
            inference_server_links += [html.Li(["Server build logs:", "not available"])]

    inference_server_info += [html.Ul(inference_server_links)]
    setup_info += [html.Li(inference_server_info)]

    setup_info += [html.Li([
        html.Details([html.Summary("Operating system: "), html.Code(yaml.dump(entry.results.system_state), style={"white-space": "pre-wrap"})]),
        html.Br(),
    ])]

    setup_info += [html.Li([
        "Model configuration",
        html.Code(yaml.dump([entry.results.test_config.get("test.model")]), style={"white-space": "pre-wrap"}),
    ])]

    if entry.results.llm_load_test_output:
        setup_info += [html.Li([
            "Llm-load-test configuration",
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
