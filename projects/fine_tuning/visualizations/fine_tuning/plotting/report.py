import copy
import logging

from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    SFTTrainerReport()
    SFTTrainerHyperParametersReport()


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


class SFTTrainerReport():
    def __init__(self):
        self.name = "report: SFTTrainer report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        header += [html.P("These plots show an overview of the metrics extracted from SFTTrainer logs.")]

        header += html.Br()
        header += html.Br()
        from ..store import parsers
        header += [html.H2("SFTTrainer Summary metrics")]

        for key in parsers.SFT_TRAINER_SUMMARY_KEYS:
            header += [html.H3(key)]
            header += Plot_and_Text("SFTTrainer Summary", set_config(dict(summary_key=key, speedup=True, efficiency=True), args))

        header += [html.H2("SFTTrainer Progress metrics")]

        for key, properties in parsers.SFT_TRAINER_PROGRESS_KEYS.items():
            if not getattr(properties, "plot", True):
                continue

            header += [html.H3(key)]
            header += Plot_and_Text("SFTTrainer Progress", set_config(dict(progress_key=key), args))


        return None, header


class SFTTrainerHyperParametersReport():
    def __init__(self):
        self.name = "report: SFTTrainer HyperParameters report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        header += [html.P("These plots show an overview of the metrics extracted from SFTTrainer logs.")]

        header += html.Br()
        header += html.Br()
        from ..store import parsers

        header += [html.H2("SFTTrainer Summary metrics. Hyper-parameters study.")]

        if "gpu" in variables:
            filter_key = "gpu"

            gpu_counts = variables.pop("gpu")
            ordered_vars.remove("gpu")
        else:
            filter_key = None
            gpu_counts = [None]

        for x_key in ordered_vars or [None]:
            if x_key is not None:
                header += [html.H2(f"by {x_key}")]

            for summary_key in parsers.SFT_TRAINER_SUMMARY_KEYS:
                header += [html.H4(f"Metric: {summary_key}")]
                for gpu_count in gpu_counts:
                    if gpu_count is not None:
                        header += [html.H4(f"with {gpu_count} GPU{'s' if gpu_count > 1 else ''} per job")]

                    header += Plot_and_Text("SFTTrainer Summary", set_config(dict(summary_key=summary_key, filter_key=filter_key, filter_value=gpu_count, x_key=x_key), args))


        return None, header
