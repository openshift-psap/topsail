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
    LtsMetric("kserve_container_cpu_usage", max, "KServe Container CPU usage", unit="max, in core")
    LtsMetric("kserve_container_memory_usage", max, "KServe Container Memory usage", unit="max, in GB", divisor=1000*1000*1000)

    LtsMetric("gpu_active_computes", max, "GPU Active compute", unit="max, in %")
    LtsMetric("gpu_memory_used", max, "GPU Memory Usage", unit="max, in GiB", divisor=1024)

    LtsMetric("rhoai_cpu_footprint_core_request", max, "RHOAI Core CPU footprint", unit="requests, in cores")
    LtsMetric("rhoai_mem_footprint_core_request", max, "RHOAI Core Memory footprint", unit="requests, in GB", divisor=1000*1000*1000)

class LtsMetric():
    def __init__(self, lts_key_name, filter_fct, descr, unit, divisor=1, higher_better=False):
        self.lts_key_name = lts_key_name
        self.filter_fct = filter_fct
        self.higher_better = higher_better
        self.descr = descr
        self.unit = unit
        self.divisor = divisor

        self.name = f"LTS: {self.descr}"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def generateLtsData(self, entries, _variables):
        data = []
        for entry in entries:
            datum = dict(name=entry.get_name(_variables),)

            all_prom_ts_values = getattr(entry.results.lts.results.metrics, self.lts_key_name)

            transformed_values = []

            for prom_ts_values in all_prom_ts_values:
                prom_values = [v / self.divisor for k, v in prom_ts_values.values.items()]
                transformed_values.append(self.filter_fct(prom_values))

            datum["value"] = self.filter_fct(transformed_values) if transformed_values else None

            data.append(datum)

        return data

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(self.generateLtsData(entries, variables))

        if df.empty:
            return None, "Not data available ..."
        fig = px.line(df, hover_data=df.columns, x="name", y="value", markers=True)
        fig.data[0].name = self.descr
        fig.data[0].showlegend = True

        list(map(fig.add_trace, get_regression_lanes(self.descr, df.name, df.value, default_op="max")))

        fig.update_layout(title=self.descr, title_x=0.5,)
        fig.update_yaxes(title=f"{'' if self.higher_better else '❮'} {self.descr} ({self.unit}) {'❯' if self.higher_better else ''}")
        fig.update_xaxes(title=f"")
        return fig, ""


def find_reference_point(df_name, df_colname, default_op):
    for name, value in zip(df_name, df_colname):
        if name.endswith("-GA"):
            return "GA", value

    return default_op, getattr(df_colname, default_op)()


def get_lane(x_col, ref_value, pct, name):
    new_value = ref_value * (1 + pct/100)

    return go.Scatter(x=x_col,
                      y=[new_value] * len(x_col),
                      name=name,
                      mode="lines",
                      line_dash="dot",
                      )

def get_regression_lanes(y_col_name, x_col, y_col, default_op):
    ref_name, ref_value = find_reference_point(x_col, y_col, default_op)

    if math.isnan(ref_value):
        return

    diff_pct = [-round((1 - y/ref_value)*100) for y in y_col if y is not None and not math.isnan(y)]

    ROUND = 5
    round_pcts = set([0, 5, -5] + [ROUND * round(pct/ROUND) for pct in diff_pct])

    for pct in sorted(round_pcts):
        name = f"{ref_name} {y_col_name}" if pct == 0 else \
            f"{pct:+d}% of the {ref_name} {y_col_name}"

        yield get_lane(x_col, ref_value, pct, name)
