from collections import defaultdict
import datetime
import statistics as stats
import logging
import datetime

from dash import html
import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    BatchJobStatus()

class BatchJobStatus():
    def __init__(self):
        self.name = "Batch Job Status"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        expe_cnt = common.Matrix.count_records(settings, setting_lists)
        if expe_cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {expe_cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            pass # entry is set

        for metric_name in "Batch Jobs Active", "Batch Jobs Complete", "Batch Jobs Failed":
            for metric in self.filter_metrics(entry, self.get_metrics(entry, metric_name)):
                if not metric: continue

                x_values = [x for x, y in metric.values.items()]
                y_values = [y/self.y_divisor for x, y in metric.values.items()]

                data.append(
                    go.Scatter(
                        x=x_values, y=y_values,
                        name=str(legend_name),
                        hoverlabel= {'namelength' :-1},
                        showlegend=self.show_legend,
                        legendgroup=legend_group,
                        legendgrouptitle_text=legend_group,
                        mode='markers+lines'))

        fig = go.Figure(data=data)

        fig.update_yaxes(title="Number of objects")
        fig.update_xaxes(title="Timeline, in minutes after the start time")

        fig.update_layout(title=f"Pod Completion Progress<br>for a total of {total_pod_count} Pods from {entry.results.target_kind_name}s", title_x=0.5)

        #fig.layout.yaxis.tickformat = ',.0%'

        return fig, ""
