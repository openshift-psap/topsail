from collections import defaultdict

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import timeline_data

def register():
    Timeline("Simple Timeline")

class Timeline():
    def __init__(self, name):
        self.name = name
        self.id_name = name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, params, param_lists, variables, cfg):

        all_XY = defaultdict(dict)
        info = defaultdict(dict)
        user_count = 0

        cnt = sum(1 for _ in common.Matrix.all_records(params, param_lists))
        if cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {cnt}."

        data = []
        for entry in common.Matrix.all_records(params, param_lists):
            user_count, data, line_sort_name = timeline_data.generate(entry)

        _df = pd.DataFrame(data)
        df = _df[_df["LegendGroup"] != "Nodes"]

        fig = px.timeline(df, x_start="Start", x_end="Finish", y="LineName", color="LegendName")
        fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
        fig.update_layout(barmode='stack', title=f"Execution timeline of {user_count} users launching a notebook ", title_x=0.5,)
        fig.update_layout(yaxis_title="")
        fig.update_layout(xaxis_title="Timeline (by date)")

        return fig, ""
