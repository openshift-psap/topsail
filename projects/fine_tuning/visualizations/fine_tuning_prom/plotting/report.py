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
    Aim()
    pass

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


class Aim():
    def __init__(self):
        self.name = "AIM"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        import sys
        sys.path.append("/usr/local/lib/python3.9/site-packages")
        import aim
        from aim.sdk.repo import Repo

        repo = Repo.from_path("/home/kpouget/kserve/aim")

        for entry in common.Matrix.all_records(settings, setting_lists):
            run = aim.Run(
                system_tracking_interval=None,
                log_system_params=False,
                capture_terminal_logs=False,
                experiment=str(entry.results.test_uuid),
            )

            for k, v in entry.settings.__dict__.items():
                run[k] = v


            for name, metric in entry.results.metrics["sutest"].items():
                if not metric: continue
                for idx, (ts, value) in enumerate(metric[0].values.items()):
                    run._tracker._track(value, ts, name, idx, context=None)

        return None, "Nothing"
