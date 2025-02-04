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
    KPITableReport("KPI Table Report by labels", labels_version=True)
    KPITableReport("KPI Table Report by settings", settings_version=True)


class KPITableReport():
    def __init__(self, name, labels_version=False, settings_version=False):
        self.name = f"report: {name}"
        self.title = name
        self.labels_version = labels_version
        self.settings_version = settings_version

        self.id_name = self.name
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, *args):
        header = [html.H1(self.title)]
        ordered_vars, settings, setting_lists, variables, cfg = args
        header += [html.P(f"Showing {common.Matrix.count_records()} tests.")]

        # --- #

        all_kpi_settings = defaultdict(set)
        for entry in common.Matrix.all_records(settings, setting_lists):
            dest_all_kpi_settings = all_kpi_settings

            entry_kpi_settings = entry.results.lts.metadata.settings

            for k, v in entry_kpi_settings.__dict__.items():
                if isinstance(v, list):
                    v = str(v)
                if not v.__hash__:
                    continue

                if k in common.LTS_META_KEYS: continue
                dest_all_kpi_settings[k].add(v)

        variable_labels = []
        fix_labels = []
        for k, v in all_kpi_settings.items():
            (variable_labels if len(v) > 1 else fix_labels).append(k)

        kpis_common_prefix = None

        all_kpi_results_data = []
        all_test_results_data = []
        kpis = None
        idx = 0

        unique_kpi_labels = set()
        for entry in common.Matrix.all_records(settings, setting_lists):
            idx += 1

            metadata = copy.copy(entry.results.lts.metadata)

            entry_kpi_results = {
                "short uuid": str(metadata.test_uuid).partition("-")[0],
                "name": entry.get_name(variables) if variables else "Unique test",
            }
            metadata_column_count = len(entry_kpi_results)
            entry_test_results = entry_kpi_results.copy()
            entry_test_results.pop("name")

            metadata_settings = copy.copy(metadata.__dict__.pop("settings"))
            for var in variable_labels:
                entry_kpi_results[var] = metadata_settings.__dict__.get(var, "missing")

            for var in variables:
                entry_test_results[var] = entry.settings.__dict__[var]

            kpis = entry.results.lts.kpis

            if kpis_common_prefix is None:
                kpis_common_prefix = analyze_report.longestCommonPrefix(list(kpis.keys()))

            for kpi_name, kpi in kpis.items():
                if isinstance(kpi.value, list): continue

                current_value_str = analyze_report.format_kpi_value(kpi)

                if (lower_better := getattr(kpi, "lower_better", None)) is not None:
                    direction = " ⮟" if lower_better else " ⮝"
                else:
                    direction = ""

                kpi_value = analyze_report.OvervallResult(
                    0, "not used", True,
                    current_value_str=current_value_str,
                )

                key_name = kpi_name.replace(kpis_common_prefix, "")
                if len(key_name) < 5:
                    key_name = kpi_name
                key_name += direction
                entry_kpi_results[key_name] = kpi_value
                entry_test_results[key_name] = kpi_value
            unique_kpi_labels.add(" ".join(f"{k}={entry_kpi_results[k]}" for k in variable_labels))
            all_kpi_results_data.append(entry_kpi_results)
            all_test_results_data.append(entry_test_results)

        kpi_names = set(list(all_kpi_results_data[0].keys())[max([metadata_column_count, len(variable_labels)+1]):]) \
            if all_kpi_results_data else set()

        if self.settings_version:
            header += [html.H2("Test Settings Overview")]

            all_settings = common.Matrix.settings.copy()
            all_settings.pop("stats")
            header.append(analyze_report._generate_configuration_overview(all_settings, variables))

            header.append(html.H2("KPI Results overview"))

            header.append(analyze_report._generate_results_overview(all_test_results_data, ordered_vars, kpi_names, kpis_common_prefix, warn=False))

        if self.labels_version:
            header += [html.H2("KPI Labels Overview")]
            header.append(analyze_report._generate_configuration_overview(all_kpi_settings, variable_labels))

            header.append(html.H2("KPI Results overview"))
            if len(unique_kpi_labels) != len(all_test_results_data):
                msg = f"found {len(unique_kpi_labels)} unique KPI labels for {len(all_test_results_data)} test entries."
                logging.warning(msg)
                header.append(html.Span([html.B("WARNING:"), msg]))

            header.append(analyze_report._generate_results_overview(all_kpi_results_data, variable_labels, kpi_names, kpis_common_prefix))


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
                    html.Li("lower is better (⮟)" if lower_better else "higher is better (⮝)"),
                ]
            header.append(html.Ul(details_elts))
            header.append(html.Br())

        if not kpis:
            header.append(html.P("No KPIs found ..."))

        return None, header
