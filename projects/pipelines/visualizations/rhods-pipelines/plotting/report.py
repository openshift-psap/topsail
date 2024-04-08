import copy
import logging

from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    UserExecutionOverviewReport()
    PodNodeMappingReport()
    ExecutionTimeDistributionReport()
    ControlPlaneReport()

def set_vars(additional_settings, ordered_vars, settings, param_lists, variables, cfg):
    _settings = dict(settings)
    _variables = copy.deepcopy(variables)
    _ordered_vars = list(ordered_vars)
    for k, v in additional_settings.items():
        _settings[k] = v
        _variables.pop(k, True)
        if k in _ordered_vars:
            _ordered_vars.remove(k)

    _param_lists = [[(key, v) for v in variables[key]] for key in _ordered_vars]

    return _ordered_vars, _settings, _param_lists, _variables, cfg

def set_config(additional_cfg, args):
    cfg = copy.deepcopy(args[-1])
    cfg.d.update(additional_cfg)
    return list(args[:-1]) + [cfg]

def set_entry(entry, _args):
    args = copy.deepcopy(_args)
    ordered_vars, settings, setting_lists, variables, cfg = args

    settings.update(entry.settings.__dict__)
    setting_lists[:] = []
    variables.clear()
    return args

def set_filters(filters, _args):
    args = copy.deepcopy(_args)
    ordered_vars, settings, setting_lists, variables, cfg = args

    for filter_key, filter_value in filters.items():
        if filter_key in variables:
            variables.pop(filter_key)
        settings[filter_key] = filter_value

        for idx, setting_list_entry in enumerate(setting_lists):
            if setting_list_entry[0][0] == filter_key:
                del setting_lists[idx]
                break

    return args

def Plot(name, args, msg_p=None):
    try:
        stats = table_stats.TableStats.stats_by_name[name]
    except KeyError:
        logging.error(f"Report: Stats '{name}' does not exist. Skipping it.")
        stats = None

    fig, msg = stats.do_plot(*args) if stats else (None, f"Stats '{name}' does not exit :/")

    if msg_p is not None: msg_p.append(msg)

    return dcc.Graph(figure=fig)

def Plot_and_Text(name, args):
    msg_p = []

    data = [Plot(name, args, msg_p)]

    if msg_p[0]:
        data.append(
            html.Div(
                msg_p[0],
                style={"border-radius": "5px",
                       "padding": "0.5em",
                       "background-color": "lightgray",
                       }))

    return data

class PodNodeMappingReport():
    def __init__(self):
        self.name = "report: Pod-Node Mapping"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.P("These plots show an overview of the mapping of the Pods on the different Nodes.")]
        header += [html.P("""The Timeline plots are useful to validate that Pods started and finished on time.""")]
        header += [html.P("""The Distribution plots are useful to visualize how the Pods were scheduled on the different Nodes.""")]

        header += [html.H2("Timeline")]

        header += [Plot(f"Pod/Node timeline", set_config(dict(dspa_only=True), args))]
        header += [html.P(f"This plot shows the timeline of the user pod mapping on the cluster's nodes, grouped by user, for the Data Science Pipelines Application Pods")]


        header += [html.H2("Pod lifespan duration")]


        header += [Plot(f"Pod lifespan duration", set_config(dict(dspa_only=True), args))]
        header += [html.P(f"This plot show the distribution of the Pod lifespan duration,for the Data Science Pipelines Application Pods")]

        return None, header

class UserExecutionOverviewReport():
    def __init__(self):
        self.name = "report: User Execution Overview"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.H2("Execution Time of the User Steps")]
        header += [Plot("User Execution Time", args)]
        header += ["This plot shows the time the simulated user took to execute each of the test steps. User IDs shown in bold font failed to pass the test. Failed steps are not shown."]

        header += [html.H2("Execution Time without the launch delay")]
        header += [Plot(f"User Execution Time", set_config({"hide_launch_delay": True}, args))]
        header += ["This plot shows the time the simulated user took to execute each of the test steps, with the test pod initialization and launch delay _hidden_."]


        header += [html.H2("Execution Time with the failed steps")]
        header += [Plot(f"User Execution Time", set_config({"keep_failed_steps": True}, args))]
        header += ["This plot shows the time the simulated user took to execute each of the test steps. User IDs shown in bold font failed to pass the test. Failed steps _are_ shown."]

        header += [html.H2("Execution Time without the failed users")]
        header += [Plot(f"User Execution Time", set_config({"hide_failed_users": True}, args))]
        header += ["This plot shows the time the simulated user took to execute each of the test steps. User who failed the test are _not_ shown."]

        header += [html.H2("Median Runtime Timeline")]
        header += Plot_and_Text(f"Median runtime timeline", args)
        header += ["This plot shows the timeline for the execution of each of the step.", html.Br(),
                   "The main bar show the media time, and the error bars show the Q1-Q3 distance.", html.Br(),
                   "This range includes 50% of the users. ", html.Br(),
                   "Only the users who succeeded the step are included in the computation.", html.Br()]

        header += [html.H2("Resource Creation timeline")]
        header += [Plot(f"Resource Creation Timeline", set_config(dict(dspa_only=True), args))]
        header += ["This plot shows the timeline of the resources creation."]

        header += [html.H2("Resource Creation Delay")]
        header += [Plot(f"Resource Creation Delay", set_config(dict(dspa_only=True), args))]
        header += ["This plot shows the delay of the resources creation: the line 'A -> B' in the legend show the delay between the creation of resource A and the creation of the resource B. Lower is better."]


        return None, header


class ExecutionTimeDistributionReport():
    def __init__(self):
        self.name = "report: Execution Time Distribution"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):

        header = []
        header += [html.P("These plots show the distribution of the user steps execution time and launch time.")]

        header += [html.H2("Median Runtime Timeline")]
        header += Plot_and_Text(f"Median runtime timeline", args)
        header += ["This plot shows the timeline for the execution of each of the step.", html.Br(),
                   "The main bar show the media time, and the error bars show the Q1-Q3 distance.", html.Br(),
                   "This range includes 50% of the users. ", html.Br(),
                   "Only the users who succeeded the step are included in the computation.", html.Br()]

        header += [html.H2("Overview of the Execution time distribution")]
        header += Plot_and_Text("Execution time distribution", set_config(dict(only_prefix=["ansible"]), args))
        header += ["This plot provides information about the execution timelength for the different user steps. The failed steps are not taken into account."]
        header += [html.Br()]
        header += [html.Br()]

        header += [html.H2("Execution time distribution for getting a usable Notebook")]

        header += ["The plots below show the break down of the execution timelength for the different steps."]

        ordered_vars, settings, setting_lists, variables, cfg = args

        if not common.Matrix.has_records(settings, setting_lists):
            return None, "No experiments available"

        for entry in common.Matrix.all_records(settings, setting_lists):
            break

        step_names = []
        for user_data in entry.results.user_data.values():
            step_names = [k for k in user_data.progress.keys() if k.startswith("ansible")]
            break

        for step_name in step_names:
            header += Plot_and_Text("Execution time distribution",
                            set_config(dict(step=step_name), args))

        return None, header


class ControlPlaneReport():
    def __init__(self):
        self.name = "report: Control Plane Nodes Load"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.H1("Control Plane Nodes Load")]

        for cluster_role in ["sutest"]:
            header += [html.H1(f"{cluster_role.title()} cluster")]

            header += ["These plots shows the CPU and memory usage of the Kubernetes API Server and ETCD, running on the Control Plane nodes of the cluster."]

            for pod_name in ["ApiServer", "ETCD"]:
                header += [html.H2(f"{pod_name} subsystem")]

                for what in ["CPU", "Mem"]:
                    header += Plot_and_Text(f"Prom: {cluster_role.title()} {pod_name}: {what} usage", args)
                    header += html.Br()
                    header += html.Br()

            if cluster_role != "sutest": continue

            header += [html.H2(f"CPU usage")]

            header += ["These plots shows the CPU usage of the Control Plane nodes.",
                       html.Br(),
                       "The first plot show all the available modes, while the second one shows only the idle time (higher is better).",
                       html.Br(),
                       "The Y scale is arbitrary, but for a given node, the sum of all the modes at a given time indicate 100% of the CPU."
                       ]

            header += Plot_and_Text(f"Prom: {cluster_role.title()} Control Plane Node CPU usage", args)
            header += html.Br()
            header += html.Br()

            header += Plot_and_Text(f"Prom: {cluster_role.title()} Control Plane Node CPU idle", args)
            header += html.Br()
            header += html.Br()

            header += Plot_and_Text(f"Prom: {cluster_role.title()} Worker Node CPU usage", args)
            header += html.Br()
            header += html.Br()

            header += Plot_and_Text(f"Prom: {cluster_role.title()} Worker Node CPU idle", args)
            header += html.Br()
            header += html.Br()

            header += [html.H2(f"APIServer requests duration")]
            for verb in ["LIST", "GET", "PUT", "PATCH"]:
                header += Plot_and_Text(f"Prom: {cluster_role.title()} API Server {verb} Requests duration", args)
                header += html.Br()
                header += html.Br()

            header += [html.H2(f"API Server HTTP return codes")]
            for what in ["successes", "client errors", "server errors"]:
                header += Plot_and_Text(f"Prom: {cluster_role.title()} API Server Requests ({what})", args)
                header += html.Br()
                header += html.Br()

        return None, header
