import copy
import logging
import itertools

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
    CpuRamUsageReport()
    LlamaBenchReport()
    LlamaMicroBenchReport()


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

        for what in ["VirtGPU Memory Usage by used", "VirtGPU Memory Usage by free"]:
            header += [html.H1(what)]
            header += report.Plot_and_Text(what, args)

        return None, header


class CpuRamUsageReport():
    def __init__(self):
        self.name = "report: CPU RAM Usage"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        for what in ["CPU Usage by idle time", "RAM Usage by unused"]:
            header += [html.H1(what)]
            header += report.Plot_and_Text(what, args)

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
        self.name = "report: Llm-load-test Results"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.H1("llm-load-test results")]

        header += report.Plot_and_Text(f"Throughput", report.set_config(dict(bar_plot=True), args))
        header += html.Br()
        header += html.Br()

        header += report.Plot_and_Text(f"Throughput", report.set_config(dict(bar_plot=True, gen_throughput=True), args))
        header += html.Br()
        header += html.Br()

        header += report.Plot_and_Text(f"Throughput", report.set_config(dict(bar_plot=True, ttft=True), args))
        header += html.Br()
        header += html.Br()

        header += report.Plot_and_Text(f"Throughput", report.set_config(dict(bar_plot=True, itl=True), args))
        header += html.Br()
        header += html.Br()

        header += report.Plot_and_Text(f"Throughput", report.set_config(dict(bar_plot=True, tpot=True), args))
        header += html.Br()
        header += html.Br()

        header += report.Plot_and_Text(f"Throughput", report.set_config(dict(ttft=True), args))
        header += html.Br()
        header += html.Br()

        header += report.Plot_and_Text(f"Throughput", report.set_config(dict(itl=True), args))
        header += html.Br()
        header += html.Br()

        header += report.Plot_and_Text(f"Throughput", report.set_config(dict(tpot=True), args))
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


class LlamaBenchReport():
    def __init__(self):
        self.name = "report: Llama-bench Results"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []

        header += [html.H1("Llama-bench results")]
        for llama_bench_test in "pp512", "tg128":
            header += [html.H1(f"llama-bench '{llama_bench_test}' test")]
            header += report.Plot_and_Text(f"Llama-bench results table", report.set_config(dict(llama_bench_test=llama_bench_test), args))
            header.pop(-2) # remove the empty plot
            header += report.Plot_and_Text(f"Llama-bench results plot", report.set_config(dict(llama_bench_test=llama_bench_test), args))
            header += html.Br()
            header += html.Br()

        return None, header


class LlamaMicroBenchReport():
    def __init__(self):
        self.name = "report: Llama-micro-bench Results"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []

        header += [html.H1("Llama.cpp micro-benchmarks results")]
        for llama_micro_bench_group in "compute", "transfer":
            header += [html.H2(f"llama.cpp micro-bench '{llama_micro_bench_group}' tests")]
            header += report.Plot_and_Text("Llama-micro-bench results plot",
                                           report.set_config(dict(group=llama_micro_bench_group), args))

            header += report.Plot_and_Text("Llama-micro-bench results table",
                                           report.set_config(dict(group=llama_micro_bench_group), args))
            header.pop(-2) # remove the empty plot

        ordered_vars, settings, setting_lists, variables, cfg = args

        if not len(ordered_vars) == 1:
            header += [html.B(f"Cannot generate the performance comparison with more than 1 variable (got: {', '.join(ordered_vars)})")]
            return None, header

        for group in "compute", "transfer":

            header += [html.H2(f"Performance Comparisons of the <i>{group}</i> operations")]

            # take all the possibilities two by two
            first_vars = variables[ordered_vars[0]]
            for ref, comp in (itertools.combinations(first_vars, 2)):
                header += report.Plot_and_Text(
                    "Llama-micro-bench comparison plot",
                    report.set_config(dict(group=group, ref=ref, comp=comp), args)
                )

        return None, header
