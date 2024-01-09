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

    metadata += [html.Li([html.B("settings:"), html.Code(", ".join(f"{k}={v}" for k, v in lts.metadata.settings.items()))])]
    metadata += [html.Li([html.B("start:"), html.Code(lts.metadata.start)])]
    metadata += [html.Li([html.B("presets:"), html.Code(", ".join(lts.metadata.presets))])]
    metadata += [html.Li([html.B("test:"), html.Code(lts.metadata.test)])]
    metadata += [html.Li([html.B("ocp_version:"), html.Code(lts.metadata.ocp_version)])]
    metadata += [html.Li([html.B("rhods_version:"), html.Code(lts.metadata.rhods_version)])]

    header += [html.Ul(metadata)]

    #import pdb;pdb.set_trace()
    header += [html.H2("data")]
    data = []

    data += [html.H3("users")]
    all_users = []

    #import pdb;pdb.set_trace()
    for idx, user in enumerate(lts.data.users):
        all_users += [html.H4(f"User #{idx}")]
        one_user = []
        one_user += [html.Li([html.B("succeeded:"), html.Code(user.succeeded)])]
        one_user += [html.Li([html.B("hostname:"), html.Code(user.hostname)])]
        # steps
        one_user += [html.Li([html.B("Steps:")])]
        steps = []
        for step in user.steps:
            steps += [html.Li(html.Code(f"{step.name}: {step.status} in {step.duration}s"))]
            if not step.substeps: continue
            steps += [html.Ul(html.Li(html.Code(", ".join(f"{k}={v}s" for k, v in step.substeps))))]

        one_user += [html.Ul(steps)]
        all_users += [html.Ul(one_user)]

    data += [html.Ul(all_users)]

    # ---

    data += [html.H3("metrics")]
    all_metrics = []
    for field_name, metric_values in lts.data.metrics.dict().items():
        all_metrics += [html.Li(html.H4(field_name))]
        field_metrics = []
        field_metrics += [html.Li(html.H5(f"key: {metric_values['query']}"))]
        for idx, values in enumerate(metric_values["data"]):
            field_metrics += [html.Li(html.H5(f"data #{idx} "))]
            field_metrics += [html.Ul([
                html.Code(", ".join(f"{k}={v}" for k, v in values["metric"].items()) or "(No metric metadata)"),
                html.Br(),html.Br(),
                html.Code(str(values["values"])),
            ])]


        all_metrics += [html.Ul(field_metrics)]

    data += [html.Ul(all_metrics)]

    # ---

    header += [html.Ul(data)]

    return header
