import copy
import logging

from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import error_report

def register():
    ControlPlaneReport()
    ComparisonReport()

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


class ControlPlaneReport():
    def __init__(self):
        self.name = "report: Control Plane Nodes Load"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []

        ordered_vars, settings, setting_lists, variables, cfg = args
        for entry in common.Matrix.all_records(settings, setting_lists):
            header += error_report._get_test_setup(entry)
            header += [html.Hr()]

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


class ComparisonReport():
    def __init__(self):
        self.name = "report: Comparison report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []

        ordered_vars, settings, setting_lists, variables, cfg = args
        for entry in common.Matrix.all_records(settings, setting_lists):
            header += error_report._get_test_setup(entry)
            header += [html.Hr()]

        header += [html.H1("Comparison report")]

        header += Plot_and_Text(f"Completion time comparison", args)
        header += Plot_and_Text(f"Execution time comparison", args)

        return None, header
