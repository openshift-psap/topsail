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

from . import report

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
            if entry.results.from_pr:
                title = html.B(entry.results.from_pr["title"])
                body = entry.results.from_pr["body"]
                if not body: body = "(empty)" # will be None if the PR body is empty

                body = body.replace("\n", "<br>")
            else:
                title = ""
                body = ""


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


            info += [html.Li(["PR ", html.A(pr.name, href=pr.link, target="_blank"), " ",title])]
            if body:
                info += [html.Ul(html.Li(html.Code(body)))]
            if last_comment_found:
                info += [html.Ul(html.Li(["Trigger date: ", html.I(last_comment_date)]))]
                info += [html.Ul(html.Li(["Trigger comment: ", html.Code(last_comment_body)]))]

            info += [html.Li(["Test diff against ", html.A(html.Code(pr.base_ref), href=pr.diff_link, target="_blank")])]


        if entry.results.from_env.link_flag == "running-with-the-test":
            results_artifacts_href = ".."
        elif entry.results.from_env.link_flag == "running-without-the-test":
            results_artifacts_href = entry.results.source_url
        else:
            results_artifacts_href = None

        info += [html.Li(html.A("Results artifacts"+(": MISSING" if not results_artifacts_href else ""),
                                href=results_artifacts_href, target="_blank"))]

        info += [html.Ul(html.Li(html.A("Dashboard configuration"+(": MISSING" if not entry.results.odh_dashboard_config_file else ""),
                                href=str(entry.results.odh_dashboard_config_file), target="_blank")))]

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
        failed_users_at_step = defaultdict(list)
        REFERENCE_USER_IDX = 0

        reference_content = None
        for user_idx, exit_code in entry.results.ods_ci_exit_code.items():
            content = []

            total_users += 1

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

            ods_ci_output = entry.results.ods_ci_output[user_idx]
            if ods_ci_output is None:
                content.append(html.Ul([
                    html.Li([f'No report available :/'])
                ]))
                failed_steps["Terminate in time"].append(content)

                continue

            for step_idx, (step_name, step_info) in enumerate(ods_ci_output.items()):
                if step_info.status != "FAIL": continue
                failed_steps[step_name].append(content)
                failed_users_at_step[step_name].append(user_idx)

                user_dir = entry.results.location / "ods-ci" / f"ods-ci-{user_idx}"
                robot_log_path = user_dir / "log.html"

                images = list(user_dir.glob("*.png"))
                images.sort(key=lambda f: int(re.findall(r"selenium-screenshot-([0-9]*).png", f.name)[0]))
                last_screenshot_path = images[-1] if images else None

                content.append(html.Ul([
                    html.Li([f'Failed at step ', html.B(html.Code(f'"ODS - {step_idx} - {step_name}".'))]),
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
                [html.Li([f"{len(contents)} users failed the step ", html.Code(step_name), " (", ", ".join(map(str, failed_users_at_step[step_name])), ")"])
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

        args = ordered_vars, settings, setting_lists, variables, cfg
        header += [html.H2("Step Successes")]
        header += [report.Plot("Step successes", args)]
        header += ["This plot shows the number of users who passed or failed each of the steps."]

        for step_name, contents in failed_steps.items():
            header.append(html.H2(f"Failed step: {step_name} x {len(contents)}"))
            for content in contents:
                header += content

        return None, header
