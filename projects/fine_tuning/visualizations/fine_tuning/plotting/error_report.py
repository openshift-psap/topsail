import copy
import re
from collections import defaultdict
import os
import base64
import pathlib
import json, yaml
import functools

from dash import html
from dash import dcc

from matrix_benchmarking.common import Matrix
import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common
from matrix_benchmarking.parse import json_dumper

import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report


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

    ocp_version = entry.results.ocp_version


    setup_info += [html.Li(["Test running on ", "OpenShift Dedicated" if managed else "OCP", html.Code(f" v{ocp_version}")])]

    nodes_info = [
        html.Li([f"Total of {len(entry.results.cluster_info.node_count)} nodes in the cluster"]),
    ]

    for purpose in ["control_plane", "infra"]:
        nodes = entry.results.cluster_info.__dict__.get(purpose)

        purpose_str = f" {purpose} nodes"
        if purpose == "control_plane": purpose_str = f" nodes running OpenShift control plane"
        if purpose == "infra": purpose_str = " nodes, running the OpenShift and RHOAI infrastructure Pods"

        if not nodes:
            node_count = 0
            node_type = "n/a"
        else:
            node_count = len(nodes)
            node_type = list(nodes)[0].instance_type

        if node_count == 0:
            continue

        nodes_info_li = [f"{node_count} ", html.Code(node_type), purpose_str]

        nodes_info += [html.Li(nodes_info_li)]

    setup_info += [html.Ul(nodes_info)]

    setup_info += [html.Li([f"Test UUID:", html.Code(entry.results.test_uuid, style={"white-space": "pre-wrap"})])]

    setup_info += [html.Li([f"Job configuration:",
                            html.Code(yaml.dump(entry.results.job_config), style={"white-space": "pre-wrap"})])]

    setup_info += [html.Li([f"Workload configuration:",
                            html.A(html.Code("config_final.json"), href=artifacts_basedir / entry.results.locations.workload_config_file, target="_blank"),
                            html.Code(yaml.dump(entry.results.workload_config), style={"white-space": "pre-wrap"})])]

    setup_info += [html.Li([f"Job execution"])]
    exec_info = []

    if entry.results.finish_reason.exit_code:
        exec_info += [html.Li([f"Exit code:", html.Code(entry.results.finish_reason.exit_code)])]
    if entry.results.finish_reason.message:
        exec_info += [html.Li([f"Exit message:", html.Code(entry.results.finish_reason.message, style={"white-space": "pre-wrap"})])]

    if entry.results.locations.has_fms:
        metrics = yaml.safe_load(json.dumps(entry.results.sfttrainer_metrics, default=functools.partial(json_dumper, strict=False)))
        if metrics and (metrics.get("progress") or metrics.get("summary")):
            exec_info += [html.Li([f"Fine-tuning metrics:", html.Code(yaml.dump(metrics), style={"white-space": "pre-wrap"})])]

    elif entry.results.locations.has_ilab:
        metrics = yaml.safe_load(json.dumps(entry.results.ilab_metrics, default=functools.partial(json_dumper, strict=False)))
        if metrics and metrics.get("progress"):
            exec_info += [html.Li([f"Fine-tuning last progress metrics:", html.Code(yaml.dump([metrics["progress"][-1]]), style={"white-space": "pre-wrap"})])]
        if metrics and metrics.get("summary"):
            exec_info += [html.Li([f"Fine-tuning summary metrics:", html.Code(yaml.dump([metrics["summary"]]), style={"white-space": "pre-wrap"})])]

    elif entry.results.locations.has_ray:
        metrics = yaml.safe_load(json.dumps(entry.results.ray_metrics, default=functools.partial(json_dumper, strict=False)))
        if metrics.get("progress") or metrics.get("summary"):
            exec_info += [html.Li([f"Fine-tuning metrics:", html.Code(yaml.dump(metrics), style={"white-space": "pre-wrap"})])]

    if entry.results.locations.job_logs:
        exec_info += [html.Li(html.A("Job logs", href=artifacts_basedir / entry.results.locations.job_logs, target="_blank"))]
    setup_info += [html.Ul(exec_info)]

    if entry.exit_code is not None:
        setup_info += [html.Li([f"Test exit code:", html.Code(entry.results.finish_reason.exit_code)])]

    return setup_info


class ErrorReport():
    def __init__(self):
        self.name = "report: Error report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        header = []

        single_expe = common.Matrix.count_records(settings, setting_lists) == 1

        for entry in common.Matrix.all_records(settings, setting_lists):
            if single_expe:
                header += [html.H1("Error Report")]
            else:
                header += [html.H1(f"Error Report: {entry.get_name(variables)}")]

            setup_info = _get_test_setup(entry)

            header += [html.Ul(
                setup_info
            )]
            header += [html.Hr()]

        return None, header
