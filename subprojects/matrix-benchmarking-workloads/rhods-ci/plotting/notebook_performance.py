from collections import defaultdict

import statistics as stats

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    NotebookPerformance("Notebook Performance")

class NotebookPerformance():
    def __init__(self, name):
        self.name = name
        self.id_name = name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        cnt = sum(1 for _ in common.Matrix.all_records(settings, setting_lists))
        if cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            break

        group_labels = ["all"]
        hist_data = [[]]
        for user_idx, ods_ci_notebook_benchmark in entry.results.ods_ci_notebook_benchmark.items():
            if not ods_ci_notebook_benchmark: continue

            #group_labels.append(f"User #{user_idx:03d}")
            hist_data[0] += ods_ci_notebook_benchmark["measures"]

        if not hist_data[0]:
            hist_data[0] += [0, 1, 2] # create_distplot crashes if there is no data at all

        # Create distplot with custom bin_size
        fig = ff.create_distplot(hist_data, group_labels, bin_size=.03)
        return fig, ""
