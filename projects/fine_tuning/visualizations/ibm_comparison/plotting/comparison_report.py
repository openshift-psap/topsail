import copy
import re
from collections import defaultdict
import os
import base64
import pathlib
import json, yaml
import functools

from dash import html
from dash import dcc

from matrix_benchmarking.common import Matrix
import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common
from matrix_benchmarking.parse import json_dumper

import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report
from . import comparison

def register():
    for metric_name in comparison.METRICS:
        ComparisonReport(metric_name)

class ComparisonReport():
    def __init__(self, metric_name):
        self.metric_name = metric_name
        self.name = f"report: {self.metric_name} Comparison"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        args = ordered_vars, settings, setting_lists, variables, cfg

        header = []
        header += [html.P("These plots show an overview of the metrics generated during the quality evaluation.")]

        if "model_name" in ordered_vars:
            ordered_vars.remove("model_name")
            model_names = variables.pop("model_name")
        else:
            model_names = [settings["model_name"]]

        title = f"Comparison report: {self.metric_name}"
        if ordered_vars:
            title += f" | {ordered_vars[-1]}"

        header += [html.H2(title)]
        for model_name in model_names:
            setting_lists[:] = []
            setting_lists += [[(key, v) for v in variables[key]] for key in ordered_vars]
            settings["model_name"] = model_name

            if len(model_names) != 1:
                header += [html.H1(model_name)]

            cfg = dict(
                metric_name=self.metric_name,
                model_name=model_name,
            )
            header += report.Plot_and_Text("Comparison", report.set_config(cfg, args))

        return None, header
