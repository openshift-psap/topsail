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
        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            image = entry.settings.__dict__["image"]
            image_name = entry.settings.__dict__["image_name"]

            if not entry.results.notebook_benchmark:
                continue

            measures = entry.results.notebook_benchmark["measures"]

            for measure_idx, measure in enumerate(measures):
                data.append(dict(Image=image,
                                 Image_name=image_name,
                                 Time=measure))


        if not data:
            return None, "No data to plot ..."

        df = pd.DataFrame(data).sort_values(by=["Image"])
        fig = px.box(df, x="Image", y="Time", color="Image_name")

        max_time = max(df["Time"])

        SET_YAXES_RANGE = False
        if SET_YAXES_RANGE:
            fig.update_yaxes(range=[0, max_time * 1.1])

        return fig, msg
