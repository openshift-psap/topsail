from collections import defaultdict

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import timeline_data

def register():
    LaunchTimeDistribution("Launch time distribution")
    LaunchTimeDistribution("Test successes", success=True)

def generate_data(entry, cfg, is_notebook):
    test_nodes = {}


class LaunchTimeDistribution():
    def __init__(self, name, success=False):
        self.name = name
        self.id_name = name
        self.success = success

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        expe_cnt = sum(1 for _ in common.Matrix.all_records(settings, setting_lists))

        if  expe_cnt != 1:
            return {}, f"ERROR: only one experiment must be selected (found {expe_cnt})"

        user_count = 0
        data = []
        line_sort_name = ""
        df = None
        for entry in common.Matrix.all_records(settings, setting_lists):
            user_count, data_timeline, line_sort_name = timeline_data.generate(entry, cfg)

        data = []
        for line in data_timeline:
            if line["LegendGroup"] != "ODS-CI": continue

            data.append(dict(
                Event=line["LegendName"],
                Time=line["Start"],
                Count=1,
                Status=line["Status"]
            ))

        df = pd.DataFrame(data)
        if self.success:
            fig = px.histogram(df, x="Event", y="Count", color="Event", pattern_shape="Status")
            fig.update_layout(title=f"Launch time distribution for {user_count} users", title_x=0.5,)
            fig.update_layout(yaxis_title="Launch date")
            fig.update_layout(xaxis_title="")
        else:
            fig = px.box(df[df["Status"] == "PASS"], x="Event", y="Time", color="Event")
            fig.update_layout(title=f"Launch time distribution for {user_count} users", title_x=0.5,)
            fig.update_layout(yaxis_title="Number of users")
            fig.update_layout(xaxis_title="")

        return fig, ""
