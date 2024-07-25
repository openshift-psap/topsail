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
    if entry.results.from_env and hasattr(entry.results.from_env, "pr"):
        pr = entry.results.from_env.pr
        if entry.results.from_pr:
            title = html.B(entry.results.from_pr["title"])
            body = entry.results.from_pr["body"]
            if not body: body = "(empty)" # will be None if the PR body is empty

            body = body.replace("\n", "<br>")
        else:
            title = ""
            body = ""

        pr_author= None
        if entry.results.from_pr:
            pr_author = entry.results.from_pr["user"]["login"]

        for comment in (entry.results.pr_comments or [])[::-1]:
            if comment["user"]["login"] != pr_author: continue
            if not comment["body"]: continue
            last_comment_body = comment["body"].replace("\n", "<br>")
            last_comment_date = comment["created_at"]
            last_comment_found = True
            break
        else:
            last_comment_found = False


        setup_info += [html.Li(["PR ", html.A(pr.name, href=pr.link, target="_blank"), " ",title])]
        if body:
            setup_info += [html.Ul(html.Li(["PR body: ", html.Code(body)]))]
        if last_comment_found:
            setup_info += [html.Ul(html.Li(["Trigger comment: ", html.Code(last_comment_body)]))]
            setup_info += [html.Ul(html.Li(["Trigger timestamp: ", html.Code(last_comment_date.replace("T", " ").replace("Z", ""))]))]

        setup_info += [html.Li([html.A("Diff", href=pr.diff_link, target="_blank"),
                                " against ",
                                html.A(html.Code(pr.base_ref), href=pr.base_link, target="_blank")])]

    artifacts_basedir = entry.results.from_local_env.artifacts_basedir

    if artifacts_basedir:
        setup_info += [html.Li(html.A("Results artifacts", href=str(artifacts_basedir), target="_blank"))]

        if entry.results.odh_dashboard_config.path:
            href = str(artifacts_basedir / entry.results.odh_dashboard_config.path)
            setup_info += [html.Ul(html.Li(html.A("Dashboard configuration", href=href, target="_blank")))]
        else:
            setup_info += [html.Ul(html.Li("Dashboard configuration: MISSING"))]
    else:
        setup_info += [html.Li(f"Results artifacts: NOT AVAILABLE ({entry.results.from_local_env.source_url})")]
        setup_info += [html.Ul(html.Li("Dashboard configuration: NOT AVAILABLE"))]

    setup_info += [html.Li("Test configuration:")]

    test_config = [html.Li(["Simulating ", html.B([html.Code(str(entry.results.user_count)), " users ..."])])]

    sleep_factor = entry.results.test_config.get("tests.notebooks.users.sleep_factor", None)
    test_config += [html.Ul(html.Li(["starting with a delay of ", html.Code(sleep_factor), " seconds"]))]

    batch_size = entry.results.test_config.get("tests.notebooks.users.batch_size", 0)
    if batch_size > 1:
        test_config += [html.Ul(html.Li(["by batches of ", html.Code(str(batch_size)), " users"]))]

    total_repeat = entry.results.test_config.get("tests.notebooks.repeat", 0)
    if total_repeat > 1:
        current_repeat = entry.settings.__dict__.get("repeat", -1)
        test_config += [html.Li(["Running repetition ", html.B([html.Code(f"#{current_repeat}"), " out of ", html.Code(str(total_repeat))])])]

    setup_info += [html.Ul(test_config)]

    managed = list(entry.results.cluster_info.control_plane)[0].managed \
        if entry.results.cluster_info.control_plane else False

    sutest_ocp_version = entry.results.ocp_version

    version_ts = entry.results.rhods_info.createdAt.strftime("%Y-%m-%d") \
        if entry.results.rhods_info.createdAt else entry.results.rhods_info.createdAt_raw

    setup_info += [html.Li([html.B("RHODS "), html.B(html.Code(f"{entry.results.rhods_info.version}-{version_ts}")), f" running on ", "OpenShift Dedicated" if managed else "OCP", html.Code(f" v{sutest_ocp_version}")])]

    nodes_info = [
        html.Li([f"Total of {len(entry.results.cluster_info.node_count)} nodes in the cluster"]),
    ]

    for purpose in ["control_plane", "infra", "rhods_compute", "test_pods_only"]:
        nodes = entry.results.cluster_info.__dict__.get(purpose)

        purpose_str = f" {purpose} nodes"
        if purpose == "control_plane": purpose_str = f" nodes running OpenShift control plane"
        if purpose == "infra": purpose_str = " nodes, running the OpenShift and RHODS infrastructure Pods"
        if purpose == "rhods_compute": purpose_str = " nodes running the Notebooks"
        if purpose == "test_pods_only": purpose_str = " nodes running the user simulation Pods"

        if purpose == "test_pods_only" and entry.results.test_config.get("clusters.driver.compute.autoscaling.enabled"):
            node_count = len(set(entry.results.testpod_hostnames.values()))
            node_type = entry.results.test_config.get("clusters.create.ocp.compute.type")
        elif not nodes:
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

    success_users = sum(1 for ods_ci in entry.results.ods_ci.values() if ods_ci and ods_ci.exit_code == 0) \
        if entry.results.ods_ci else 0

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

        failed_steps = defaultdict(list)
        failed_users_at_step = defaultdict(list)
        REFERENCE_USER_IDX = 0

        reference_content = None
        for user_idx, ods_ci in entry.results.ods_ci.items() if entry.results.ods_ci else {}:

            content = []

            if ods_ci and ods_ci.exit_code == 0:
                if user_idx != REFERENCE_USER_IDX: continue

                robot_log_path = pathlib.Path("ods-ci") / f"ods-ci-{user_idx}" / "log.html"
                content.append(html.Ul([
                    html.Li([html.A("ODS-CI logs", target="_blank", href=artifacts_link(robot_log_path)), " (reference run)"]),
                ]))

                reference_content = content
                continue

            content.append(html.H3(f"User #{user_idx}"))

            if ods_ci is None:
                content.append(html.Ul([
                    html.Li([f'No data collected :/'])
                ]))
                step_name = "No data collected"

                failed_steps[step_name].append(content)
                failed_users_at_step[step_name].append(user_idx)
                continue

            if ods_ci.output is None:
                content.append(html.Ul([
                    html.Li([f'No report available :/'])
                ]))
                step_name = "Terminate in time"
                failed_steps[step_name].append(content)
                failed_users_at_step[step_name].append(user_idx)
                continue

            for step_idx, (step_name, step_info) in enumerate(ods_ci.output.items()):
                if step_info.status != "FAIL": continue
                failed_steps[step_name].append(content)
                failed_users_at_step[step_name].append(user_idx)

                user_dir = pathlib.Path("ods-ci") / f"ods-ci-{user_idx}"
                robot_log_path = user_dir / "log.html"

                last_screenshot_path = user_dir / "final_screenshot.png"

                content.append(html.Ul([
                    html.Li([f'Failed at step ', html.B(html.Code(f'"ODS - {step_idx} - {step_name}".'))]),
                    html.Li(html.A("ODS-CI logs", target="_blank", href=artifacts_link(robot_log_path))),
                ]))

                if last_screenshot_path:
                    content += [html.A(html.Img(src=artifacts_link(last_screenshot_path),
                                                width=1024,
                                                style={"border": "2px solid #555", "border-radius": "25px"}),
                                       target="_blank", href=artifacts_link(last_screenshot_path))]
                else:
                    content += [html.I("No screenshot available.")]

                break

        missing_results = entry.results.user_count - len(entry.results.ods_ci)
        missing_exit_code = sum(1 for ods_ci in entry.results.ods_ci.values() if not ods_ci or ods_ci.exit_code is None)

        HIDE_USER_DETAILS_THRESHOLD = 10
        steps = html.Ul(
            ([html.Li(f"{missing_results} users didn't report any result (test infra issue)")] if missing_results else [])
            +
            ([html.Li(f"{missing_exit_code} users didn't report their completion status (test infra issue)")] if missing_exit_code else [])
            +
            list(
                [html.Li([f"{len(contents)} users failed the step ", html.Code(step_name)] + ([" (", ", ".join(map(str, failed_users_at_step[step_name])), ")"] if len(contents) < HIDE_USER_DETAILS_THRESHOLD else []))
                 for step_name, contents in failed_steps.items()]
            )

        )

        header += [html.Ul(
            setup_info
            + [steps]
        )]

        if reference_content:
            header.append(html.H2("Reference run"))
            header += reference_content

        args = ordered_vars, settings, setting_lists, variables, cfg
        header += [html.H2("Step Successes")]
        header += [report.Plot("Step successes", args)]
        header += ["This plot shows the number of users who passed or failed each of the steps."]

        for step_name, contents in failed_steps.items():
            header.append(html.H2(f"Failed step: {step_name} x {len(contents)}"))
            for content in contents:
                header += content

        return None, header
