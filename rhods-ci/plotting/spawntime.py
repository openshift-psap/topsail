from collections import defaultdict

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import timeline_data

def register():
    SpawnTime("Notebook spawn time")

class SpawnTime():
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

        data_timeline = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            user_count, data_timeline, line_sort_name = timeline_data.generate(entry, cfg)

        data = []
        for line in data_timeline:
            if line["LegendGroup"] != "ODS-CI": continue

            hide = cfg.get("hide", None)
            if isinstance(hide, int):
                if f"User #{hide:2d}" == line["LineName"]: continue
            elif isinstance(hide, str):
                skip = False
                for hide_idx in hide.split(","):
                    print(f"User #{int(hide_idx): 2d}", line["LineName"])
                    if f"User #{int(hide_idx):2d}" == line["LineName"]: skip = True
                if skip: continue

            line_data = line.copy()
            line_data["Length"] = (line_data["Finish"] - line_data["Start"]).total_seconds() / 60
            line_data["Test step"] = line_data["LegendName"]
            data.append(line_data)

        df = pd.DataFrame(data)
        fig = px.area(df, y="LineName", x="Length", color="Test step")
        fig.update_layout(xaxis_title="Timeline (in minutes)")
        fig.update_layout(yaxis_title="")

        return fig, ""
