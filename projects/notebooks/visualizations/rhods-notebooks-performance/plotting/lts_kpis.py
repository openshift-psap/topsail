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
    report_LTS_KPIs()
    LTS_KPIs()


class report_LTS_KPIs():
    def __init__(self):
        self.name = "report: LTS: KPIs"
        self.id_name = self.name
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []
        ordered_vars, settings, setting_lists, variables, cfg = args

        header += [html.H1("LTS: KPIs")]
        header += [html.H2(f"Overview (all the images)")]
        header += report.Plot_and_Text("LTS: KPIs", args)
        header += report.Plot_and_Text("LTS: KPIs", report.set_config(dict(by_diff=True), args))

        image_names = set(image.partition(":")[0] for image in common.LTS_Matrix.settings["image"])
        for image_name in sorted(image_names):
            header += [html.H2(f"Image: {image_name}")]
            header += report.Plot_and_Text("LTS: KPIs", report.set_config(dict(image_name=image_name), args))

            header += report.Plot_and_Text("LTS: KPIs", report.set_config(dict(image_name=image_name, by_diff=True), args))
            header += report.Plot_and_Text("LTS: KPIs", report.set_config(dict(image_name=image_name, by_tag=True), args))

        header += [html.Hr()]
        return None, header


def generateLTSKPI(entry_results, filters={}):
    entry_kpis = entry_results.kpis

    entry_settings = "<br>"+"<br>".join(f"<b>{k}</b>={v}" for k, v in entry_results.kpis.notebook_performance_benchmark_time.__dict__.items() if k not in ("value", "timestamp", "unit", "description"))


    timestamp = entry_kpis.notebook_performance_benchmark_min_max_diff.timestamp
    rhoai_version = entry_kpis.notebook_performance_benchmark_min_max_diff.rhoai_version

    kpi_ref = entry_kpis.notebook_performance_benchmark_min_max_diff
    for filter_name, filter_value in filters.items():
        if getattr(kpi_ref, filter_name, None) != filter_value:
            return []

    entry_data = dict(
        timestamp = timestamp,
        settings = entry_settings,

        image_name = kpi_ref.image_name,
        image_tag = kpi_ref.image_tag,
        image = f"{kpi_ref.image_name}:{kpi_ref.image_tag}",

        rhoai_version = kpi_ref.rhoai_version,

        notebook_performance_benchmark_min_time = entry_kpis.notebook_performance_benchmark_min_time.value,
        notebook_performance_benchmark_time = entry_kpis.notebook_performance_benchmark_time.value,
        notebook_performance_benchmark_min_max_diff = entry_kpis.notebook_performance_benchmark_min_max_diff.value,
    )

    return [entry_data]


class LTS_KPIs():
    def __init__(self):
        self.name = "LTS: KPIs"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        cfg__image_name = cfg.get("image_name", False)
        cfg__by_tag = cfg.get("by_tag", False)
        cfg__by_diff = cfg.get("by_diff", False)

        cnt = common.LTS_Matrix.count_records()
        if cnt == 0:
            return {}, f"ERROR: no LTS matrix entry found :/"

        filters = dict(image_name=cfg__image_name) if cfg__image_name else {}

        data = []
        for entry in common.LTS_Matrix.all_records():
            for an_entry in entry.results if entry.is_gathered else [entry]:
                data += generateLTSKPI(an_entry.results, filters=filters)

        if cfg__by_diff:
            y_key = "notebook_performance_benchmark_min_max_diff"
        else:
            y_key = "notebook_performance_benchmark_min_time"


        if not data:
            return {}, f"ERROR: no LTS matrix entry found with {filters}:/"

        df = pd.DataFrame(data)
        if cfg__by_tag:
            df = df.sort_values(by=["image_tag", y_key])

            fig = px.line(df, x="image_tag",
                          y=y_key,
                          hover_data=df.columns,
                          markers=True)
            subtitle = f"by tags of image `{cfg__image_name}`"
        else:
            df = df.sort_values(by=["rhoai_version", y_key])
            if filters:
                color_key = "image_tag"
            else:
                color_key = "image"

            fig = px.line(df, x="rhoai_version",
                          y=y_key, color=color_key,
                          hover_data=df.columns,
                          markers=True)
            fig.update_xaxes(title="RHOAI version")
            subtitle = f"by image tag and RHOAI version"
            if cfg__image_name:
                subtitle += f", for image `{cfg__image_name}`"

        fig.update_yaxes(zeroline=True, range=(0, max(df[y_key]) * 1.1))
        fig.update_yaxes(title="❮ Benchmark execution time, in seconds. (Lower is better.)")

        what = "min/max diff" if cfg__by_diff else "fastest result"
        title = f"Notebook images performance ({what})<br>{subtitle}"
        fig.update_layout(title=title, title_x=0.5)

        return fig, []
