from collections import defaultdict
import re
import logging
import datetime
import math
import copy

import statistics as stats

import plotly.subplots
import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import report

def register():
    LtsDocumentationReport()


class LtsDocumentationReport():
    def __init__(self):
        self.name = "report: LTS Documentation"
        self.id_name = self.name
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, *args):
        header = []
        ordered_vars, settings, setting_lists, variables, cfg = args

        for entry in common.Matrix.all_records(settings, setting_lists):
            header += [html.H1(entry.get_name(variables or [s for s in settings.keys() if s != "stats"]))]
            header += generateOneLtsDocumentationReport(entry)
            header += [html.Hr()]
        return None, header

def generateOneLtsDocumentationReport(entry):
    lts = entry.results.lts

    header = []
    header += [html.H2("metadata")]
    metadata = []

    metadata += [html.Li([html.B("settings:"), html.Code(f"{k}: {v}" for k, v in lts.metadata.settings.items())])]
    metadata += [html.Li([html.B("start:"), html.Code(lts.metadata.start)])]
    metadata += [html.Li([html.B("presets:"), html.Code(", ".join(lts.metadata.presets))])]
    metadata += [html.Li([html.B("config:"), html.Code("(not shown for clarity)")])]
    gpus = []
    for gpu in lts.metadata.gpus:
        gpus.append(html.Li(html.Code(", ".join(f"{k}={v}" for k, v in gpu.__dict__.items()))))
    metadata += [html.Li([html.B("GPUs:"), html.Ul(gpus)])]

    header += [html.Ul(metadata)]

    header += [html.H2("results")]
    results = []

    results += [html.H3("metrics")]
    all_metrics = []
    for field_name, metric_values in lts.results.metrics.dict().items():
        all_metrics += [html.Li(html.H4(field_name))]
        field_metrics = []
        for idx, metric_value in enumerate(metric_values):
            field_metrics += [html.Li(html.H5(f"#{idx} metric/value"))]
            field_metrics += [html.Ul([
                html.Code(", ".join(f"{k}={v}" for k, v in metric_value["metric"].items()) or "(No metric metadata)"),
                html.Br(),html.Br(),
                html.Code(str(metric_value["values"])),
            ])]

        all_metrics += [html.Ul(field_metrics)]



    results += [html.Ul(all_metrics)]

    header += [html.Ul(results)]

    return header
