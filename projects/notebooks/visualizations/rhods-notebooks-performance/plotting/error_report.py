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

    if artifacts_basedir:
        setup_info += [html.Li(html.A("Results artifacts", href=str(artifacts_basedir), target="_blank"))]

    else:
        setup_info += [html.Li(f"Results artifacts: NOT AVAILABLE ({entry.results.from_local_env.source_url})")]

    managed = list(entry.results.cluster_info.control_plane)[0].managed \
        if entry.results.cluster_info.control_plane else False

    sutest_ocp_version = entry.results.sutest_ocp_version


    setup_info += [html.Li(["Test running on ", "OpenShift Dedicated" if managed else "OCP", html.Code(f" v{sutest_ocp_version}")])]

    nodes_info = [
        html.Li([f"Total of {len(entry.results.cluster_info.node_count)} nodes in the cluster"]),
    ]

    for purpose in ["control_plane", "infra"]:
        nodes = entry.results.cluster_info.__dict__.get(purpose)

        purpose_str = f" {purpose} nodes"
        if purpose == "control_plane": purpose_str = f" nodes running OpenShift control plane"
        if purpose == "infra": purpose_str = " nodes, running the OpenShift and RHODS infrastructure Pods"

        if not nodes:
            node_count = 0
            node_type = "n/a"
        else:
            node_count = len(nodes)
            node_type = list(nodes)[0].instance_type

        nodes_info_li = [f"{node_count} ", html.Code(node_type), purpose_str]

        nodes_info += [html.Li(nodes_info_li)]

    setup_info += [html.Ul(nodes_info)]

    return setup_info

class ErrorReport():
    def __init__(self):
        self.name = "report: Error report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if common.Matrix.count_records(settings, setting_lists) != 1:
            return {}, "ERROR: only one experiment must be selected"

        for entry in common.Matrix.all_records(settings, setting_lists):
            pass

        header = []
        header += [html.P("This report shows the list of users who failed the test, with a link to their execution report and the last screenshot taken by the Robot.")]
        header += [html.H1("Error Report")]

        setup_info = _get_test_setup(entry)

        if entry.results.from_local_env.is_interactive:
            # running in interactive mode
            def artifacts_link(path):
                if path.suffix != ".png":
                    return f"file://{entry.results.from_local_env.artifacts_basedir / path}"
                try:
                    with open (entry.results.from_local_env.artifacts_basedir / path, "rb") as f:
                        encoded_image = base64.b64encode(f.read()).decode("ascii")
                        return f"data:image/png;base64,{encoded_image}"
                except FileNotFoundError:
                    return f"file://{entry.results.from_local_env.artifacts_basedir / path}#file_not_found"
        else:
            artifacts_link = lambda path: entry.results.from_local_env.artifacts_basedir / path


        header += [html.Ul(
            setup_info
        )]

        return None, header
