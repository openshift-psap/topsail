

from collections import defaultdict
import re
import logging
import datetime
import math
import copy
import numbers
import numpy
import statistics as stats

import plotly.subplots
import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common


def register():
    QualityEvaluation()


def generateQualityData(entry):
    data = []
    for line in entry.results.quality_evaluation:
        data.append(dict(name=line["color"], value=int(line["value"][1:], 16)))
    return data


class QualityEvaluation():
    def __init__(self):
        self.name = "Group Accuracies"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        single_expe = common.Matrix.count_records(settings, setting_lists) == 1

        if not single_expe:
            return None, ["Only one expe was expected..."]

        for entry in common.Matrix.all_records(settings, setting_lists):
            pass # entry is set

        accuracies = entry.results.group_accuracies

        df = pd.DataFrame(list(accuracies.items()), columns=['Group', 'Accuracy'])
        if df.empty:
            return None, "Nothing to plot"

        fig = px.bar(df, hover_data=df.columns, x="Group", y="Accuracy", barmode='group')

        fig.update_xaxes(title="Group")
        fig.update_yaxes(title="Accuracy")

        title = "Group Accuracies"

        fig.update_layout(title=title, title_x=0.5,)
        fig.update_layout(legend_title_text="Group Accuracies")

        msg = ["A text-based evaluation can go there."]

        return fig, msg