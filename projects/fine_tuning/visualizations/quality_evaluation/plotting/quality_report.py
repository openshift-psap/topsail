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

from . import report

def register():
    QualityReport()


class QualityReport():
    def __init__(self):
        self.name = "report: Quality report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        args = ordered_vars, settings, setting_lists, variables, cfg

        header = []
        header += [html.P("These plots show an overview of the metrics generated during the quality evaluation.")]

        header += [html.H2("Quality evaluation report")]

        header += report.Plot_and_Text("Quality Evaluation", args)

        return None, header
