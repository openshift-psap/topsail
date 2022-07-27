import copy
import re
from collections import defaultdict
import os
import base64

from dash import html
from dash import dcc

from matrix_benchmarking.common import Matrix
import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    ErrorReport()

class ErrorReport():
    def __init__(self):
        self.name = "report: Error report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if sum(1 for _ in common.Matrix.all_records(settings, setting_lists)) != 1:
            return {}, "ERROR: only one experiment must be selected"

        for entry in common.Matrix.all_records(settings, setting_lists):
            pass

        header = []
        header += [html.P("This report shows the list of users who failed the test, with a link to their execution report and the last screenshot taken by the Robot.")]
        header += [html.H1("Error Report")]

        info = []
        if entry.results.from_env.pr:
            pr = entry.results.from_env.pr
            info += [html.Li(["PR ", html.A(pr.name, href=pr.link, target="_blank"), html.B(entry.results.from_pr["title"])])]
            info += [html.Ul(html.Li(html.Code(entry.results.from_pr["body"].replace("\n", "<br>"))))]
            info += [html.Li(["Test diff against ", html.A(html.Code(pr.base_ref), href=pr.diff_link, target="_blank")])]

        if entry.results.from_env.link_flag == "running-with-the-test":
            info += [html.Li(html.A("Results artifacts",
                                    href="..", target="_blank"))]
        elif entry.results.from_env.link_flag == "running-without-the-test":
            info += [html.Li(html.A("Results artifacts",
                                    href=entry.results.source_url, target="_blank"))]

        info += [html.Li(["RHODS ", html.Code(entry.results.rhods_info.version)])]

        info += [html.Li(["Test job: ", html.Code(entry.results.from_env.env.get("JOB_NAME_SAFE", "no job defined"))])]
        managed = list(entry.results.nodes_info.values())[0].managed
        ocp_version = entry.results.rhods_info.ocp_version
        info += [html.Li(["Running on ", "OpenShift Dedicated" if managed else "OCP", f" v{ocp_version}"])]
        if entry.results.from_env.link_flag == "interactive" :
            # running in interactive mode
            def link(path):
                if path.suffix != ".png":
                    return f"file://{path}"

                with open (path, "rb") as f:
                    encoded_image = base64.b64encode(f.read()).decode("ascii")
                return f"data:image/png;base64,{encoded_image}"

        else:
            if entry.results.from_env.link_flag == "running-locally":
                # not running in the CI
                link = lambda path: f"file://{path}"

            elif entry.results.from_env.link_flag == "running-with-the-test":
                # running right after the test
                link = lambda path: str(".." / path.relative_to(entry.results.location.parent))

            elif entry.results.from_env.link_flag == "running-without-the-test":
                # running independently of the test

                link = lambda path: f"{entry.results.source_url}/{path.relative_to(entry.results.location.parent)}"
            else:
                raise ValueError(f"Unexpected value for 'entry.results.link_flag' env var: '{entry.results.link_flag}'")

        total_users = 0
        failed_users = 0
        failed_steps = defaultdict(list)
        REFERENCE_USER_IDX = 0

        reference_content = None
        for podname, exit_code in entry.results.ods_ci_exit_code.items():
            content = []

            total_users += 1

            user_idx = int(podname.split("-")[2])
            if exit_code == 0:
                if user_idx != REFERENCE_USER_IDX: continue

                user_dir = entry.results.location / "ods-ci" / f"ods-ci-{user_idx}"
                robot_log_path = user_dir / "log.html"
                content.append(html.Ul([
                    html.Li([html.A("ODS-CI logs", target="_blank", href=link(robot_log_path)), " (reference run)"]),
                ]))

                reference_content = content
                continue

            content.append(html.H3(f"User #{user_idx}"))
            failed_users += 1

            ods_ci_output = entry.results.ods_ci_output[podname]
            if ods_ci_output is None:
                content.append(html.Ul([
                    html.Li([f'No report available :/'])
                ]))
                failed_steps["Terminate in time"].append(content)
                continue

            for step_idx, (step_name, step_info) in enumerate(ods_ci_output.items()):
                if step_info.status != "FAIL": continue
                failed_steps[step_name].append(content)

                user_dir = entry.results.location / "ods-ci" / f"ods-ci-{user_idx}"
                robot_log_path = user_dir / "log.html"

                images = list(user_dir.glob("*.png"))
                images.sort(key=lambda f: int(re.findall(r"selenium-screenshot-([0-9]*).png", f.name)[0]))
                last_screenshot_path = images[-1] if images else None

                content.append(html.Ul([
                    html.Li([f'Failed at step', html.B(html.Code(f'"ODS - {step_idx} - {step_name}".'))]),
                    html.Li(html.A("ODS-CI logs", target="_blank", href=link(robot_log_path))),
                ]))

                if last_screenshot_path:
                    content += [html.A(html.Img(src=link(last_screenshot_path),
                                                width=1024,
                                                style={"border": "2px solid #555", "border-radius": "25px"}),
                                       target="_blank", href=link(last_screenshot_path))]
                else:
                    content += [html.I("No screenshot available.")]

                break

        steps = html.Ul(
            list(
                [html.Li([f"{len(contents)} users failed the step ", html.Code(step_name)])
                 for step_name, contents in failed_steps.items()]
            )

        )
        header += [html.Ul(
            info
            + [html.Li(f"{failed_users}/{total_users} users failed:" if failed_users else f"None of the {total_users} users failed.")]
            + [steps]
        )]

        if reference_content:
            header.append(html.H2("Reference run"))
            header += reference_content

        for step_name, contents in failed_steps.items():
            header.append(html.H2(f"Failed step: {step_name} x {len(contents)}"))
            for content in contents:
                header += content

        return None, header
