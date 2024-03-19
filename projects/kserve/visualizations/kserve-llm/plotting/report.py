import copy
import logging

from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    LatencyReport()
    ThroughputReport()
    TokensReport()
    LtsReport()

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

class LatencyReport():
    def __init__(self):
        self.name = "report: Latency per token"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args
        collapse_index = "mode" in variables

        header = []
        header += [html.H1("Latency per token during the load test")]

        if not collapse_index:
            header += Plot_and_Text(f"Latency distribution", set_config(dict(box_plot=False, show_text=False), args))

        header += Plot_and_Text(f"Latency details", args)
        header += html.Br()
        header += html.Br()

        header += Plot_and_Text(f"Latency distribution", args)

        header += html.Br()
        header += html.Br()

        if collapse_index:
            header += [html.H3("Latency per token, with all the indexes aggregated")]
            header += Plot_and_Text(f"Latency distribution", set_config(dict(collapse_index=collapse_index, show_text=False), args))
            header += Plot_and_Text(f"Latency distribution", set_config(dict(collapse_index=collapse_index, box_plot=False), args))

        DISABLE_DETAILS = True
        if DISABLE_DETAILS:
            return None, header

        ordered_vars, settings, setting_lists, variables, cfg = args
        for entry in common.Matrix.all_records(settings, setting_lists):
            header += [html.H2(entry.get_name(reversed(sorted(set(list(variables.keys()) + ['model_name'])))))]
            header += Plot_and_Text(f"Latency details", set_config(dict(entry=entry), args))

        return None, header


class ThroughputReport():
    def __init__(self):
        self.name = "report: Throughput"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.H1("llm-load-test Thoughput")]

        header += Plot_and_Text(f"Throughput", set_config(dict(bar_plot=True), args))
        header += html.Br()
        header += html.Br()

        header += Plot_and_Text(f"Throughput", set_config(dict(), args))
        header += html.Br()
        header += html.Br()

        header += Plot_and_Text(f"Throughput", set_config(dict(itl=True), args))
        header += html.Br()
        header += html.Br()

        header += Plot_and_Text(f"TTFT Concurrency", set_config(dict(), args))
        header += html.Br()
        header += html.Br()

        ordered_vars, settings, setting_lists, variables, cfg = args
        for model_name in variables.get("model_name", []):
            header += [html.H1(f"Thoughput of model {model_name}")]

            header += Plot_and_Text(f"Throughput", set_config(dict(bar_plot=True, model_name=model_name), args))
            header += Plot_and_Text(f"Throughput", set_config(dict(model_name=model_name), args))
            header += Plot_and_Text(f"Throughput", set_config(dict(model_name=model_name, itl=True), args))
            header += Plot_and_Text(f"TTFT Concurrency", set_config(dict(model_name=model_name), args))
            header += html.Br()
            header += html.Br()

        return None, header


class TokensReport():
    def __init__(self):
        self.name = "report: Tokens"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.H1("llm-load-test tokens")]

        header += Plot_and_Text(f"Finish Reason distribution", args)
        header += html.Br()
        header += html.Br()

        header += Plot_and_Text(f"Latency distribution", set_config(dict(only_tokens=True), args))
        header += html.Br()
        header += html.Br()
        header += Plot_and_Text(f"Latency details", set_config(dict(only_tokens=True), args))

        DISABLE_DETAILS = True

        if DISABLE_DETAILS:
            return None, header

        ordered_vars, settings, setting_lists, variables, cfg = args
        for entry in common.Matrix.all_records(settings, setting_lists):
            header += [html.H2(entry.get_name(reversed(sorted(set(list(variables.keys()) + ['model_name'])))))]
            header += Plot_and_Text(f"Latency details", set_config(dict(only_tokens=True, entry=entry), args))

        return None, header


class LtsReport():
    def __init__(self):
        self.name = "report: LTS"
        self.id_name = self.name
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, *args):
        header = []
        header += [html.H1("LTS visualization")]

        header += Plot_and_Text(f"LTS: Throughput", args)
        header += html.Br()
        header += html.Br()

        header += Plot_and_Text(f"LTS: Time Per Output Token", args)
        header += html.Br()
        header += html.Br()

        header += Plot_and_Text(f"LTS: Model Load Time", args)
        header += html.Br()
        header += html.Br()

        return None, header
