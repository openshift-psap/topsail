from collections import defaultdict

import statistics as stats

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    PodTimes()

def generatePodTimes(entry):
    data = []
    for p in entry.results.pods_info:
        print(p)
        pod = { 
            "Start": p.start_time,
            "End": p.container_finished,
            "Duration": (p.container_finished - p.start_time).seconds,
            "Pod": p.pod_name,
            "Node": p.hostname
        }
        data.append(pod)

    return data

class PodTimes():
    def __init__(self):
        self.name = "Pod time distribution"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        print(settings)
        cnt = common.Matrix.count_records(settings, setting_lists)
        if cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            break

        data = generatePodTimes(entry)

        if not data:
            return None, "No data to plot ..."

        df = pd.DataFrame(data)

        fig = px.histogram(df, x="Duration",
                           marginal="box",
                           barmode="overlay",
                           hover_data=df.columns)
        fig.update_layout(xaxis_title="Pod time to complete (seconds)")

        title = f"Distribution of the runtime for coreutils build pods"

        fig.update_layout(title=title, title_x=0.5)

        msg = []

        return fig, msg
