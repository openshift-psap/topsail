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

import matrix_benchmarking.analyze.report as analyze_report

from packaging.version import Version, InvalidVersion

def register():
    KPITableReport()

class KPITableReport():
    def __init__(self):
        self.name = "report: KPI Table Report"
        self.id_name = self.name
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, *args):
        header = []
        ordered_vars, settings, setting_lists, variables, cfg = args

        header += [html.H1("")]

        all_regr_results_data = []
        idx = 0

        all_settings = defaultdict(set)
        for entry in common.Matrix.all_records(settings, setting_lists):
            dest_all_settings = all_settings

            entry_settings = entry.results.lts.metadata.settings

            for k, v in entry_settings.__dict__.items():
                if isinstance(v, list):
                    v = str(v)
                if not v.__hash__:
                    continue

                if k in common.LTS_META_KEYS: continue
                dest_all_settings[k].add(v)

        kpi_variables = []
        fix_settings = []
        for k, v in all_settings.items():
            (kpi_variables if len(v) > 1 else fix_settings).append(k)

        kpis_common_prefix = None

        kpis = None
        for entry in common.Matrix.all_records(settings, setting_lists):
            idx += 1

            metadata = copy.copy(entry.results.lts.metadata)
            entry_regr_results = dict(uuid=metadata.test_uuid)
            metadata_settings = copy.copy(metadata.__dict__.pop("settings"))
            for var in kpi_variables:
                entry_regr_results[var] = metadata_settings.__dict__.get(var, "missing")

            if not kpi_variables:
                entry_regr_results["name"] = "Unique test"

            kpis = entry.results.lts.kpis

            if kpis_common_prefix is None:
                kpis_common_prefix = analyze_report.longestCommonPrefix(list(kpis.keys()))

            for kpi_name, kpi in kpis.items():
                if isinstance(kpi.value, list): continue

                current_value_str = analyze_report.format_kpi_value(kpi)
                entry_regr_results[kpi_name.replace(kpis_common_prefix, "")] = \
                    analyze_report.OvervallResult(
                        0, "not used", True,
                        current_value_str=current_value_str)

            all_regr_results_data.append(entry_regr_results)

        header.append(html.H2("KPI Results overview"))
        kpi_names = set(list(all_regr_results_data[0].keys())[max([2, len(kpi_variables)+1]):]) \
            if all_regr_results_data else set()

        header.append(analyze_report._generate_results_overview(all_regr_results_data, kpi_variables, kpi_names, kpis_common_prefix))

        if kpis:
            header.append(html.H2("KPIs description"))

            for kpi_name, kpi in kpis.items():
                header.append(html.B(kpi_name))
                details_elts = [
                    html.Li(html.I(kpi.help)),
                    html.Li(f"in {kpi.unit}"),
                ]

                if divisor_unit := getattr(kpi, "divisor_unit", None):
                    details_elts += [
                        html.Li(f"converted into {divisor_unit}"),
                    ]
                if (lower_better := getattr(kpi, "lower_better", None)) is not None:
                    details_elts += [
                        html.Li("Lower is better" if lower_better else "Higher is better"),
                    ]
                header.append(html.Ul(details_elts))
                header.append(html.Br())

        return None, header
