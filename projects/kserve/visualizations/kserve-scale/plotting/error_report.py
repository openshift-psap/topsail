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

from . import report

def register():
    ErrorReport()


def _get_all_tests_setup(args):
    header = []

    ordered_vars, settings, setting_lists, variables, cfg = args
    for entry in common.Matrix.all_records(settings, setting_lists):
        header += _get_test_setup(entry)
        header += [html.Hr()]

    return header


def _get_test_setup(entry):
    setup_info = []

    artifacts_basedir = entry.results.from_local_env.artifacts_basedir

    if artifacts_basedir:
        setup_info += [html.Li(html.A("Results artifacts", href=str(artifacts_basedir), target="_blank"))]

    else:
        setup_info += [html.Li(f"Results artifacts: NOT AVAILABLE ({entry.results.from_local_env.source_url})")]

    setup_info += [html.Br()]

    managed = list(entry.results.cluster_info.control_plane)[0].managed \
        if entry.results.cluster_info.control_plane else False

    sutest_ocp_version = entry.results.sutest_ocp_version

    version = "version not available"
    if entry.results.rhods_info:
        version_ts = entry.results.rhods_info.createdAt.strftime("%Y-%m-%d") \
            if entry.results.rhods_info.createdAt else entry.results.rhods_info.createdAt_raw
        version = f"{entry.results.rhods_info.version}-{version_ts}"

    setup_info += [html.Li([html.B("RHODS "), html.B(html.Code(version)), f" running on ", "OpenShift Dedicated" if managed else "OCP", html.Code(f" v{sutest_ocp_version}")])]

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

    test_config_file = entry.results.from_local_env.artifacts_basedir / entry.results.file_locations.test_config_file

    setup_info += [html.Br()]

    total_users = entry.results.user_count
    success_users = entry.results.success_count
    setup_info += [html.Li(f"{success_users}/{total_users} users succeeded")]
    setup_info += [html.Br()]

    setup_info += [html.Li([html.A("Test configuration:", href=str(test_config_file), target="_blank"), html.Code(yaml.dump(dict(tests=dict(scale=entry.results.test_config.yaml_file["tests"]["scale"]))), style={"white-space": "pre-wrap"})])]

    return setup_info

class ErrorReport():
    def __init__(self):
        self.name = "report: Error report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

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

        setup_info += [html.Li(["RHOAI configuration: ", html.Code(yaml.dump(dict(rhods=entry.results.test_config.yaml_file["rhods"])), style={"white-space": "pre-wrap"})])]

        setup_info += [html.Li(["KServe configuration: ", html.Code(yaml.dump(dict(watsonx_serving=entry.results.test_config.yaml_file["kserve"])), style={"white-space": "pre-wrap"})])]

        header += report.Plot_and_Text(f"Inference Services Progress", args)
        header += report.Plot_and_Text(f"Inference Services Load-time Distribution", args)

        failed_users = []
        successful_users = []

        for user_index, user_data in entry.results.user_data.items():
             content = []
             content.append(html.H3(f"User #{user_index}"))
             user_links = []
             user_links.append(html.Li(html.A("Execution logs", target="_blank", href=artifacts_link(user_data.artifact_dir / "run.log"))))
             user_links.append(html.Li(html.A("Execution artifacts", target="_blank", href=artifacts_link(user_data.artifact_dir))))
             content.append(html.Ul(user_links))
             content.append(html.Br())

             dest = successful_users if user_data.exit_code == 0 else failed_users
             dest.append(content)

        if failed_users:
            header.append(html.H2(f"Failed users x {len(failed_users)}"))
            for user in failed_users:
                header += user

        if successful_users:
            header.append(html.H2(f"Successful users x {len(successful_users)}"))
            for user in successful_users:
                header += user


        return None, header
