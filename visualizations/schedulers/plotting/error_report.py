import copy
import re
from collections import defaultdict
import os
import base64
import pathlib
import yaml

from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common
import matrix_benchmarking.cli_args as cli_args

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

    test_config_file = entry.results.from_local_env.artifacts_basedir / entry.results.file_locations.test_config_file
    setup_info += [html.Li(html.A("Test configuration", href=str(test_config_file), target="_blank"))]

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

    setup_info += [html.Li(["Test duration: ", html.Code(f"{entry.results.lts.results.test_duration/60:.1f} minutes"), "for", html.Code([str(entry.results.test_case_properties.count), entry.results.target_kind_name])])]

    setup_info += [html.Ul(html.Li(["Test throughput of ", html.Code(f"{entry.results.lts.results.actual_throughput:.2f} {entry.results.target_kind_name}/minute")]))]
    setup_info += [html.Ul(html.Ul(html.Li([f"Average time per job:", html.Code(f"{entry.results.lts.results.avg_time_per_job:.2f} seconds")])))]

    setup_info += [html.Ul(html.Li([f"{entry.results.target_kind_name} theoretical throughput of ", html.Code(f"{entry.results.lts.results.job_theoretical_throughput:.2f} {entry.results.target_kind_name}/minute")]))]
    setup_info += [html.Ul(html.Ul(html.Li([f" median runtime:", html.Code(f"{entry.results.lts.results.job_median_runtime:.2f} seconds")])))]

    setup_info += [html.Ul(html.Li([f"Pod theoretical throughput of ", html.Code(f"{entry.results.lts.results.pod_theoretical_throughput:.2f} Pod/minute")]))]
    setup_info += [html.Ul(html.Ul(html.Li([f"median runtime:", html.Code(f"{entry.results.lts.results.pod_median_runtime:.2f} seconds")])))]
    setup_info += [html.Li(["Max concurrency: ", html.Code(f"{entry.results.lts.results.max_concurrency} Pods running simultaneously")])]

    time_to_last_schedule_sec = entry.results.lts.results.time_to_last_schedule_sec
    time_to_last_launch_sec = entry.results.lts.results.time_to_last_launch_sec
    last_launch_to_last_schedule_sec = entry.results.lts.results.last_launch_to_last_schedule_sec

    def time(sec):
        if sec <= 120:
            return f"{sec:.0f} seconds"
        else:
            return f"{sec/60:.1f} minutes"

    def _get_time_to_cleanup(results):
        if not results.cleanup_times:
            return 0

        start = results.cleanup_times.start
        end = results.cleanup_times.end
        if not (start and end):
            return 0

        return (end - start).total_seconds()

    if last_launch_to_last_schedule_sec:
        setup_info += [html.Li(["Time to last Pod schedule: ", html.Code(f"{time_to_last_schedule_sec/60:.1f} minutes")])]
        setup_info += [html.Ul(html.Li(["Test speed of ", html.Code(f"{time_to_last_schedule_sec/60:.2f} Pods/minute")]))]
        setup_info += [html.Ul(html.Li(["Time between the last resource launch and its schedule: ", html.Code(f"{last_launch_to_last_schedule_sec} seconds")]))]

    if entry.results.cleanup_times:
        time_to_cleanup_sec = _get_time_to_cleanup(results)
        setup_info += [html.Ul(html.Li([f"Time to cleanup: ", html.Code(f"{time(time_to_cleanup_sec)}")]))]

    setup_info += [html.Li(["Test-case configuration: ", html.B(getattr(entry.settings, "name", "")), html.Code(yaml.dump(entry.results.test_case_config), style={"white-space": "pre-wrap"})])]
    return setup_info


class ErrorReport():
    def __init__(self):
        self.name = "report: Error report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def _do_plot_multi(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []
        header += [html.P("This report shows a summary of the test setups.")]
        header += [html.H1("Error Report")]

        header += [html.Ul(html.Li(f"{common.Matrix.count_records(settings, setting_lists)} tests are taken into account in this batch."))]

        results_dirname = pathlib.Path(cli_args.kwargs["results_dirname"])

        settings_list = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            test_location = html.Span(str(entry.location.relative_to(results_dirname)))
            entry_settings = html.Code(", ".join(([f"{key}={value}" for key, value in entry.settings.__dict__.items() if len(common.Matrix.settings[key]) > 1])))

            settings_list.append(html.Ul([html.Li(entry_settings), html.Ul(html.Li(test_location))]))

        header += [html.Ul(settings_list)]

        for entry in common.Matrix.all_records(settings, setting_lists):
            header += [html.Hr()]
            entry_settings = html.Code(", ".join(([f"{key}={value}" for key, value in entry.settings.__dict__.items() if len(common.Matrix.settings[key]) > 1])))

            header += [html.H2(entry_settings)]

            header += _get_test_setup(entry)

        return None, header

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        if common.Matrix.count_records(settings, setting_lists) != 1:
            return self._do_plot_multi(*args)

        for entry in common.Matrix.all_records(settings, setting_lists):
            pass

        header = []
        header += [html.P("This report shows a summary of the test setup and some key performance indicators.")]
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

        header += [html.H2(f"{entry.results.target_kind_name} Completion Progress")]

        header += report.Plot_and_Text(f"Pod Completion Progress", args)
        header += html.Br()
        header += html.Br()

        header += report.Plot_and_Text(f"Resource Mapping Timeline", args)

        header += report.Plot_and_Text(f"Resource Mapping Timeline", report.set_config(dict(all_at_once=True), args))
        header += report.Plot_and_Text(f"Resource Mapping Timeline", report.set_config(dict(all_at_once=True, by_pod=True), args))

        header += report.Plot_and_Text(f"Waiting Time Distribution", args)
        header += report.Plot_and_Text(f"Waiting Time Timeline", args)
        header += report.Plot_and_Text(f"Scheduling Order", args)

        return None, header
