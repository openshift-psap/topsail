from collections import defaultdict
import re
import logging
import datetime
import math
import copy
import yaml

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

    metadata += [html.Li([html.B("settings:"), html.Code(", ".join(f"{k}={v}" for k, v in dict(lts.metadata.settings).items()))])]
    metadata += [html.Li([html.B("start:"), html.Code(lts.metadata.start)])]
    metadata += [html.Li([html.B("presets:"), html.Code(", ".join(lts.metadata.presets))])]
    metadata += [html.Li([html.B("test:"), html.Code(lts.metadata.test)])]
    metadata += [html.Li([html.B("ocp_version:"), html.Code(lts.metadata.ocp_version)])]
    metadata += [html.Li([html.B("rhods_version:"), html.Code(lts.metadata.rhods_version)])]
    metadata += [html.Li([html.B("config:"), html.Code("(not shown for clarity)")])]

    metadata += [html.Li([html.B("ci_engine:"), html.Code(lts.metadata.ci_engine)])]
    metadata += [html.Li([html.B("run_id:"), html.Code(lts.metadata.run_id)])]
    metadata += [html.Li([html.B("test_path:"), html.Code(lts.metadata.test_path)])]

    urls = []
    for name, url in (lts.metadata.urls or {}).items():
        urls += [html.Li(html.A(name, target="_blank", href=url))]
    metadata += [html.Li([html.B("URLs:"), html.Ul(urls)])]

    header += [html.Ul(metadata)]

    header += [html.H2("kpis")]
    kpis = []
    for name, kpi in lts.kpis:
        labels = {k:v for k, v in kpi.__dict__.items() if k not in ("unit", "help", "timestamp", "value")}
        labels_str = ", ".join(f"{k}=\"{v}\"" for k, v in labels.items())
        kpis += [html.Li([html.P([html.Code(f"# HELP {name} {kpi.help}"), html.Br(),
                                  html.Code(f"# UNIT {name} {kpi.unit}"), html.Br(),
                                  html.Code(f"{name}{{{labels_str}}} {kpi.value}")])])]

    header += [html.Ul(kpis)]

    header += [html.H2("results")]
    results = []
    results += [html.H2("benchmark measures")]
    benchmark_measures = []
    benchmark_measures += [html.Li([html.B("benchmark:"), html.Code(lts.results.benchmark_measures.benchmark)])]
    benchmark_measures += [html.Li([html.B("repeat:"), html.Code(lts.results.benchmark_measures.repeat)])]
    benchmark_measures += [html.Li([html.B("number:"), html.Code(lts.results.benchmark_measures.number)])]
    benchmark_measures += [html.Li([html.B("measures:"), html.Code(lts.results.benchmark_measures.measures)])]

    results += [html.Ul(benchmark_measures)]
    header += [html.Ul(results)]

    regression = []
    regression += [html.H1("regression analysis")]
    regression += [html.Code(yaml.dump([dict(r) for r in lts.regression], default_flow_style=False), style={"white-space": "pre-wrap"})]

    header += [html.Ul(regression)]

    return header
