import copy
import logging

from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

try:
    from . import error_report
except ImportError:
    error_report = None

def register():
    UserProgressReport()
    UserProgressDetailsReport()

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


class UserProgressReport():
    def __init__(self):
        self.name = "report: User Progress"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []

        header += error_report._get_all_tests_setup(args)

        header += [html.H1("User Progress")]

        header += [Plot(f"User progress", args)]
        header += [Plot(f"User progress", set_config(dict(hide_launch_delay=False), args))]

        header += Plot_and_Text(f"Resource Creation Delay", set_config(dict(as_distribution=True), args))

        header += [html.H1("GRPC calls distribution")]
        header += Plot_and_Text(f"GRPC calls distribution", set_config(dict(show_attempts=False), args))
        header += Plot_and_Text(f"GRPC calls distribution", set_config(dict(show_attempts=True), args))

        header += [html.H1("Resource Creation")]

        header += Plot_and_Text(f"Inference Services Progress", args)

        header += Plot_and_Text(f"Interval Between Creations", args)

        header += Plot_and_Text(f"Resource Creation Timeline", args)

        header += Plot_and_Text(f"Resource Creation Delay", set_config(dict(model_id=None), args))

        header += [html.H1("Resource Conditions")]

        for kind in ("InferenceService", "Revision"):
            header += Plot_and_Text(f"Conditions Timeline", set_config(dict(kind=kind), args))

            header += Plot_and_Text(f"Conditions in State Timeline", set_config(dict(kind=kind), args))

        return None, header


class UserProgressDetailsReport():
    def __init__(self):
        self.name = "report: User Progress Details"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []

        header += error_report._get_all_tests_setup(args)

        header += [html.H1("Resource Creation")]

        ordered_vars, settings, setting_lists, variables, cfg = args
        for entry in common.Matrix.all_records(settings, setting_lists):
            models_per_ns = entry.results.test_config.get("tests.scale.model.replicas")
            for model_id in range(models_per_ns):
                header += Plot_and_Text(f"Resource Creation Delay", set_config(dict(model_id=model_id), args))

        return None, header
