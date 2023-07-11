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
    for resource_name, resource_times in entry.results.resource_times.items():
        print(resource_name)
        print(resource_times)
        if resource_times.kind != "Pod": continue

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

        cnt = common.Matrix.count_records(settings, setting_lists)
        if cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            break

        cfg__show_only_state = cfg.get("state", False)

        data = generatePodTimes(entry)

        if not data:
            return None, "No data to plot ..."

        df = pd.DataFrame(data)

        if cfg__show_only_state:
            df = df[df.State == cfg__show_only_state]

        fig = px.histogram(df, x="Duration",
                           color="State",
                           marginal="box",
                           barmode="overlay",
                           hover_data=df.columns)
        fig.update_layout(xaxis_title="Step timelength (in seconds)")

        if cfg__show_only_state:
            title = f"Distribution of the time spent<br>in the <b>{cfg__show_only_state}</b> AppWrapper state"
            fig.layout.update(showlegend=False)
        else:
            title = f"Distribution of the time spent in each of the different AppWrappers state"

        fig.update_layout(title=title, title_x=0.5)

        msg = []

        return fig, msg
