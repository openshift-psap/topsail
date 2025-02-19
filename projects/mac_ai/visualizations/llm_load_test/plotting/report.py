import copy
import logging

from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report


def register():
    LatencyReport()
    ThroughputReport()
    TokensReport()
    CallDetailsReport()
    LtsReport()
    GPUUsageReport()

class CallDetailsReport():
    def __init__(self):
        self.name = "report: Call details"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        for model_name in common.Matrix.settings.get("model_name", []):
            header += [html.H1(f"{model_name}")]
            header += report.Plot_and_Text(f"Latency details",
                                           report.set_config(dict(
                                               model_name=model_name, color="duration",
                                               legend_title="Call duration,<br>in s", show_timeline=True), args))
            header += report.Plot_and_Text(f"Latency details",
                                           report.set_config(dict(
                                               model_name=model_name, color="tpot",
                                               legend_title="TPOT,<br>in ms/token", show_timeline=True), args))
            header += report.Plot_and_Text(f"Latency details",
                                           report.set_config(dict(
                                               model_name=model_name, color="ttft",
                                               legend_title="TTFT,<br>in ms", show_timeline=True), args))
            header += report.Plot_and_Text(f"Latency details",
                                           report.set_config(dict(
                                               model_name=model_name, color="itl",
                                               legend_title="ITL,<br>in ms", show_timeline=True), args))
            header += report.Plot_and_Text(f"Latency details",
                                           report.set_config(dict(model_name=model_name, only_ttft=True), args))

        return None, header


class GPUUsageReport():
    def __init__(self):
        self.name = "report: GPU Usage"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        for what in ["by power", "by idle", "by frequency"]:
            plot_name = f"GPU Usage {what}"
            header += [html.H1(plot_name)]
            header += report.Plot_and_Text(plot_name, args)

        return None, header


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
            header += report.Plot_and_Text(f"Latency distribution", report.set_config(dict(box_plot=False, show_text=False), args))

        header += report.Plot_and_Text(f"Latency details", args)
        header += html.Br()
        header += html.Br()

        header += report.Plot_and_Text(f"Latency distribution", args)

        header += html.Br()
        header += html.Br()

        if collapse_index:
            header += [html.H3("Latency per token, with all the indexes aggregated")]
            header += report.Plot_and_Text(f"Latency distribution", report.set_config(dict(collapse_index=collapse_index, show_text=False), args))
            header += report.Plot_and_Text(f"Latency distribution", report.set_config(dict(collapse_index=collapse_index, box_plot=False), args))

        DISABLE_DETAILS = True
        if DISABLE_DETAILS:
            return None, header

        ordered_vars, settings, setting_lists, variables, cfg = args
        for entry in common.Matrix.all_records(settings, setting_lists):
            header += [html.H2(entry.get_name(reversed(sorted(set(list(variables.keys()) + ['model_name'])))))]
            header += report.Plot_and_Text(f"Latency details", report.set_config(dict(entry=entry), args))

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
        header += [html.H1("llm-load-test Throughput")]

        header += report.Plot_and_Text(f"Throughput", report.set_config(dict(bar_plot=True), args))
        header += html.Br()
        header += html.Br()

        header += report.Plot_and_Text(f"Throughput", report.set_config(dict(), args))
        header += html.Br()
        header += html.Br()

        header += report.Plot_and_Text(f"Throughput", report.set_config(dict(itl=True), args))
        header += html.Br()
        header += html.Br()

        header += report.Plot_and_Text(f"By Users", report.set_config(dict(what="throughput"), args))
        header += html.Br()
        header += html.Br()

        header += report.Plot_and_Text(f"By Users", report.set_config(dict(what="ttft"), args))
        header += html.Br()
        header += html.Br()

        ordered_vars, settings, setting_lists, variables, cfg = args
        for model_name in common.Matrix.settings.get("model_name", []):
            header += [html.H1(f"Thoughput of model {model_name}")]

            header += report.Plot_and_Text(f"Throughput", report.set_config(dict(bar_plot=True, model_name=model_name), args))
            header += report.Plot_and_Text(f"Throughput", report.set_config(dict(model_name=model_name), args))
            header += report.Plot_and_Text(f"Throughput", report.set_config(dict(model_name=model_name, itl=True), args))
            header += report.Plot_and_Text(f"By Users", report.set_config(dict(model_name=model_name, what="throughput"), args))
            header += report.Plot_and_Text(f"By Users", report.set_config(dict(model_name=model_name, what="ttft"), args))
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

        header += report.Plot_and_Text(f"Finish Reason distribution", args)
        header += html.Br()
        header += html.Br()

        header += report.Plot_and_Text(f"Latency distribution", report.set_config(dict(only_tokens=True), args))
        header += html.Br()
        header += html.Br()
        header += report.Plot_and_Text(f"Latency details", report.set_config(dict(only_tokens=True), args))

        DISABLE_DETAILS = True

        if DISABLE_DETAILS:
            return None, header

        ordered_vars, settings, setting_lists, variables, cfg = args
        for entry in common.Matrix.all_records(settings, setting_lists):
            header += [html.H2(entry.get_name(reversed(sorted(set(list(variables.keys()) + ['model_name'])))))]
            header += report.Plot_and_Text(f"Latency details", report.set_config(dict(only_tokens=True, entry=entry), args))

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

        header += report.Plot_and_Text(f"LTS: Throughput", args)
        header += html.Br()
        header += html.Br()

        header += report.Plot_and_Text(f"LTS: Time Per Output Token", args)
        header += html.Br()
        header += html.Br()


        return None, header
