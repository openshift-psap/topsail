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
        setup_info += [html.Ul(html.Li("Dashboard configuration: NOT AVAILABLE"))]

    setup_info += [html.Li("Test configuration:")]

    test_config = [html.Li(["Simulating ", html.B([html.Code(str(entry.results.user_count)), " users ..."])])]

    sleep_factor = entry.results.test_config.get("tests.pipelines.sleep_factor", None)
    test_config += [html.Ul(html.Li(["starting with a delay of ", html.Code(sleep_factor), " seconds"]))]

    batch_size = entry.results.test_config.get("tests.pipelines.batch_size", 0)
    if batch_size > 1:
        test_config += [html.Ul(html.Li(["by batches of ", html.Code(str(batch_size)), " users"]))]

    setup_info += [html.Ul(test_config)]

    managed = list(entry.results.cluster_info.control_plane)[0].managed \
        if entry.results.cluster_info.control_plane else False

    sutest_ocp_version = entry.results.ocp_version

    setup_info += [html.Li([html.B("RHODS "), html.B(html.Code(f"{entry.results.rhods_info.full_version}")), f" running on ", "OpenShift Dedicated" if managed else "OCP", html.Code(f" v{sutest_ocp_version}")])]

    nodes_info = [
        html.Li([f"Total of {len(entry.results.cluster_info.node_count)} nodes in the cluster"]),
    ]

    for purpose in ["control_plane", "infra", "rhods_compute", "test_pods_only"]:
        nodes = entry.results.cluster_info.__dict__.get(purpose)

        purpose_str = f" {purpose} nodes"
        if purpose == "control_plane": purpose_str = f" nodes running OpenShift control plane"
        if purpose == "infra": purpose_str = " nodes, running the OpenShift and RHODS infrastructure Pods"
        if purpose == "rhods_compute": purpose_str = " nodes running the user pods (notebooks and pipelines)"
        if purpose == "test_pods_only": purpose_str = " nodes running the user simulation Pods"

        if not nodes:
            node_count = 0
            node_type = "n/a"
        else:
            node_count = len(nodes)
            node_type = list(nodes)[0].instance_type

        nodes_info_li = [f"{node_count} ", html.Code(node_type), purpose_str]

        nodes_info += [html.Li(nodes_info_li)]

        if purpose == "rhods_compute":
            sutest_autoscaling = entry.results.test_config.get("clusters.sutest.compute.autoscaling.enabled", False)
            if sutest_autoscaling:
                auto_scaling_msg = ["Auto-scaling ", html.I("enabled"), "."]
            else:
                auto_scaling_msg = ["Nodes scaled up ", html.I("before"), " the test."]
            nodes_info += [html.Ul(html.Li(auto_scaling_msg))]

            sutest_spot = entry.results.test_config.get("clusters.sutest.compute.machineset.spot", False)
            if sutest_spot:
                nodes_info += [html.Ul(html.Li(["Running on ", html.I("AWS Spot"), " instances."]))]

        elif purpose == "test_pods_only":
            single_cluster = entry.results.test_config.get("clusters.create.type") == "single"
            if single_cluster:
                nodes_info += [html.Ul(html.Li(["Test pods running on the ", html.I("same"), " cluster."]))]
            else:
                nodes_info += [html.Ul(html.Li(["Test pods running on ", html.I("another"), " cluster."]))]

            driver_autoscaling = entry.results.test_config.get("clusters.driver.compute.autoscaling.enabled", False)
            if driver_autoscaling:
                nodes_info += [html.Ul(html.Li(["Auto-scaling ", html.I("enabled"), "."]))]

            driver_spot = entry.results.test_config.get("clusters.driver.compute.machineset.spot", False)
            if driver_spot:
                nodes_info += [html.Ul(html.Li(["Running on ", html.I("AWS Spot instances.")]))]

    setup_info += [html.Ul(nodes_info)]

    total_users = entry.results.user_count

    success_users = entry.results.success_count

    setup_info += [html.Li(f"{success_users}/{total_users} users succeeded")]

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
