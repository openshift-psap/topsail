from collections import defaultdict

import statistics as stats

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    PythonPerformance("Notebook Python Performance Comparison")

class PythonPerformance():
    def __init__(self, name):
        self.name = name
        self.id_name = name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        threshold_status_keys = set()
        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            entry_name = ", ".join([f"{key}={entry.settings.__dict__[key]}" for key in variables])

            try: check_thresholds = entry.results.check_thresholds
            except AttributeError: check_thresholds = False

            if check_thresholds:
                threshold_status_keys.add(entry_name)

            threshold = float(entry.results.thresholds.get("py_perf_threshold", 0)) or None

            for user_idx, ods_ci in entry.results.ods_ci.items() if entry.results.ods_ci else []:
                if not ods_ci.notebook_benchmark: continue

                measures = ods_ci.notebook_benchmark["measures"]

                for measure_idx, measure in enumerate(measures):
                    data.append(dict(EntryName=entry_name,
                                     Time=measure,
                                     Threshold=threshold))




        if not data:
            return None, "No data to plot ..."

        df = pd.DataFrame(data).sort_values(by=["EntryName"])
        fig = px.box(df, x="EntryName", y="Time", color="EntryName")

        if 'Threshold' in df and not df["Threshold"].isnull().all():
            fig.add_scatter(name="Test threshold",
                            x=df['EntryName'], y=df['Threshold'], mode='lines+markers',
                            marker=dict(color='red', size=15, symbol="triangle-down"),
                            line=dict(color='black', width=3, dash='dot'))

        msg = []
        for entry_name in threshold_status_keys:
            res = df[df["EntryName"] == entry_name]
            if res.empty:
                msg.append(html.B(f"{entry_name}: no data ..."))
                msg.append(html.Br())
                continue

            threshold = float(res["Threshold"].values[0])
            value_90 = res["Time"].quantile(0.90)
            test_passed = value_90 <= threshold
            success_count = 1 if test_passed else 0
            msg += [html.B(entry_name), ": ", html.B("PASSED" if test_passed else "FAILED"), f" ({success_count}/1 success{'es' if success_count > 1 else ''})"]

            if test_passed:
                msg.append(html.Ul(html.Li(f"PASS: {value_90:.1f} seconds <= threshold={threshold:.1f} seconds")))
            else:
                msg.append(html.Ul(html.Li(f"FAIL: {value_90:.1f} seconds > threshold={threshold:.1f} seconds")))
        return fig, msg
