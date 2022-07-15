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

        keep_failed_steps = cfg.get("keep_failed_steps", False)
        hide_failed_users = cfg.get("hide_failed_users", False)

        for line in data_timeline:
            if line["LegendGroup"] != "ODS-CI": continue
            failures = entry.results.ods_ci_user_test_status[line["UserIdx"]]
            if failures and hide_failed_users: continue

            if line["LegendName"].startswith("ODS - 0 -"):
                entry_data = line.copy()

                entry_data["Test step"] = "Launch delay and initialization"
                entry_data["Length"] = (entry_data["Start"] - entry.results.job_creation_time).total_seconds()
                entry_data["StepIdx"] = -1
                if failures:
                    entry_data["LineName"] = f"<b>{entry_data['LineName']}</b>"

                data.insert(0, entry_data)

            hide = cfg.get("hide", None)
            if isinstance(hide, int):
                if f"User #{hide:2d}" == line["LineName"]: continue

            elif isinstance(hide, str):
                skip = False
                for hide_idx in hide.split(","):
                    if f"User #{int(hide_idx):2d}" == line["LineName"]: skip = True
                if skip: continue

            line_data = line.copy()
            if keep_failed_steps or line_data["Status"] == "PASS":
                line_data["Length"] = (line_data["Finish"] - line_data["Start"]).total_seconds()
            else:
                line_data["Length"] = 0

            line_data["Test step"] = line_data["LegendName"]

            if failures:
                line_data["LineName"] = f"<b>{line_data['LineName']}</b>"

            data.append(line_data)

        if not data:
            return {}, "No data available"

        df = pd.DataFrame(data).sort_values(by=['UserIdx', "StepIdx"], ascending=True)

        fig = px.area(df, y="LineName", x="Length", color="Test step")
        fig.update_layout(xaxis_title="Timeline (in seconds)")
        fig.update_layout(yaxis_title="")
        fig.update_yaxes(autorange="reversed") # otherwise users are listed from the bottom up
        title = "Execution Time of the User Steps"
        if keep_failed_steps:
            title += " with the failed steps"
        if hide_failed_users:
            title += " without the failed users"
        fig.update_layout(title=title, title_x=0.5,)
        return fig, ""
