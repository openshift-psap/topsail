import copy
import re
from collections import defaultdict
import os

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


        job_name = os.getenv("JOB_NAME_SAFE", None)
        if not job_name:
            link = lambda path: f"file://{path}"
        elif job_name.startswith("jh-on-"):
            link = lambda path: str(".." / path.relative_to(entry.results.location.parent))
        elif job_name.startswith("plot-jh-on-"):
            if entry.results.source_url is None:
                raise ValueError(f"'source_url' value not available for {entry.results.location} ...")
            link = lambda path: entry.results.source_url + "/" + str(path.relative_to(entry.results.location.parent))
        else:
            raise ValueError(f"Unexpected value for 'JOB_NAME_SAFE' env var: '{job_name}'")

        content = []
        total_users = 0
        failed_users = 0
        failed_steps = defaultdict(int)
        REFERENCE_USER_IDX = 0
        for podname, exit_code in entry.results.ods_ci_exit_code.items():
            total_users += 1

            user_idx = int(podname.split("-")[2])
            if exit_code == 0 and user_idx != REFERENCE_USER_IDX: continue

            content.append(html.H2(f"User #{user_idx}"))

            if exit_code == 0 and user_idx == REFERENCE_USER_IDX:
                user_dir = entry.results.location / "ods-ci" / f"ods-ci-{user_idx}"
                robot_log_path = user_dir / "log.html"
                content.append(html.Ul([
                    html.Li([html.A("ODS-CI logs", target="_blank", href=link(robot_log_path)), " (reference run)"]),
                ]))
                continue

            failed_users += 1

            ods_ci_output = entry.results.ods_ci_output[podname]
            if ods_ci_output is None:
                content.append(html.Ul([
                    html.Li([f'No report available :/'])
                ]))
                failed_steps["Terminate in time"] += 1
                continue

            for step_idx, (step_name, step_info) in enumerate(ods_ci_output.items()):
                if step_info.status != "FAIL": continue
                failed_steps[step_name] += 1

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
                                                style="border: 2px solid #555; border-radius: 25px;"),
                                       target="_blank", href=link(last_screenshot_path))]
                else:
                    content += [html.I("No screenshot available.")]

                break

        steps = html.Ul(
            list(
                [html.Li([f"{cnt} users failed the step ", html.Code(step_name)])
                 for step_name, cnt in failed_steps.items()]
            )

        )
        header += [html.Ul(
            [html.Li(f"{failed_users}/{total_users} users failed:")]
            + [steps]
        )]

        return None, header + content
