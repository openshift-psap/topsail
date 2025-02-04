import copy
import logging

from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report


def register():
    TrainingReport(flavor="SFTTrainer")
    TrainingHyperParametersReport(flavor="SFTTrainer")
    TrainingReport(flavor="ILab")
    TrainingHyperParametersReport(flavor="ILab")

    RayBenchmarkReport()


class TrainingReport():
    def __init__(self, flavor):
        self.flavor = flavor
        self.name = f"report: {self.flavor} report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True
        from ..store import parsers

        self.summary_keys = parsers.SFT_TRAINER_SUMMARY_KEYS if flavor == "SFTTrainer" \
            else parsers.ILAB_SUMMARY_KEYS

        self.progress_keys = parsers.SFT_TRAINER_PROGRESS_KEYS if flavor == "SFTTrainer" \
            else parsers.ILAB_PROGRESS_KEYS

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        header += [html.P(f"These plots show an overview of the metrics extracted from {self.flavor} logs.")]

        header += html.Br()
        header += html.Br()
        from ..store import parsers
        header += [html.H2(f"{self.flavor} Summary metrics")]

        for key in self.summary_keys.keys():
            header += [html.H3(key)]
            header += report.Plot_and_Text(f"{self.flavor} Summary",
                                           report.set_config(dict(summary_key=key, speedup=True, efficiency=True), args))

        header += [html.H2(f"{self.flavor} Progress metrics")]

        for key, properties in self.progress_keys.items():
            if not getattr(properties, "plot", True):
                continue

            header += [html.H3(key)]
            header += report.Plot_and_Text(f"{self.flavor} Progress",
                                           report.set_config(dict(progress_key=key), args))


        return None, header


class TrainingHyperParametersReport():
    def __init__(self, flavor):
        self.flavor = flavor
        self.name = f"report: {self.flavor} HyperParameters report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        from ..store import parsers

        self.summary_keys = parsers.SFT_TRAINER_SUMMARY_KEYS if flavor == "SFTTrainer" \
            else (parsers.ILAB_SUMMARY_KEYS | parsers.ILAB_PROGRESS_KEYS)

        self.progress_keys = parsers.SFT_TRAINER_PROGRESS_KEYS if flavor == "SFTTrainer" \
            else parsers.ILAB_PROGRESS_KEYS

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        header += [html.P(f"These plots show an overview of the metrics extracted from {self.flavor} logs.")]

        header += html.Br()
        header += html.Br()
        from ..store import parsers

        header += [html.H2(f"{self.flavor} Summary metrics. Hyper-parameters study.")]

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

            for summary_key in self.summary_keys.keys():
                header += [html.H4(f"Metric: {summary_key}")]
                for gpu_count in gpu_counts:
                    if gpu_count is not None:
                        header += [html.H4(f"with {gpu_count} GPU{'s' if gpu_count > 1 else ''} per job")]

                    header += report.Plot_and_Text(f"{self.flavor} Summary",
                                                   report.set_config(
                                                       dict(summary_key=summary_key, filter_key=filter_key, filter_value=gpu_count, x_key=x_key),
                                                       args))


        return None, header


class RayBenchmarkReport():
    def __init__(self):
        self.name = "report: Ray Benchmark report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        header += [html.P("These plots show an overview of the metrics extracted from Ray logs.")]

        header += html.Br()
        header += html.Br()

        header += [html.H2("Ray Benchmark Summary metrics.")]


        for x_key in list(ordered_vars) or [None]:
            if x_key is not None:
                header += [html.H2(f"by {x_key}")]

                ordered_vars.remove(x_key)
                ordered_vars.insert(0, x_key)

            header += report.Plot_and_Text("Ray Benchmark Summary",
                                           args)


        return None, header
