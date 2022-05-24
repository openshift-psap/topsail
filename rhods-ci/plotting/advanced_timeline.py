from collections import defaultdict
import datetime

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import timeline_data

def register():
    Timeline("Timeline")

class Timeline():
    def __init__(self, name):
        self.name = name
        self.id_name = name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        if sum(1 for _ in common.Matrix.all_records(settings, setting_lists)) != 1:
            return {}, "ERROR: only one experiment must be selected"

        user_count = 0
        data = []
        line_sort_name = ""
        for entry in common.Matrix.all_records(settings, setting_lists):
            user_count, data, line_sort_name = timeline_data.generate(entry)

        # ---

        df = pd.DataFrame(data)

        ordered_lines = list(df[df["LegendName"] == line_sort_name].sort_values("LineSortIndex")["LineName"].unique())
        for line_name in df["LineName"].unique():
            if line_name in ordered_lines:
                continue
            ordered_lines.append(line_name)

        min_date = []
        max_date = []
        plots = []
        for legend_name in df["LegendName"].unique():
            rows = df[df["LegendName"] == legend_name]

            def get_optional_scalar(column_name):
                return None if (column_name not in rows or rows[column_name].isnull().values[0]) \
                    else rows[column_name].values[0]

            x = []
            y = []
            text = []
            for row in range(len(rows)):
                line_idx = ordered_lines.index(rows["LineName"].values[row])
                txt = rows["Text"].values[row]

                get_ts = lambda name: datetime.datetime.fromtimestamp(int(rows[name].values[row].astype(datetime.datetime))/1000000000)

                current_ts = get_ts("Start")
                while current_ts < get_ts("Finish"):
                    x += [current_ts]
                    y += [line_idx]
                    text += [txt]
                    current_ts += datetime.timedelta(minutes=1)
                    if get_optional_scalar("SkipFromMinMaxDate"):
                        break

                x += [get_ts("Finish"), None]
                y += [line_idx, None]
                text += [txt, None]

                # The None values above tells Plotly not to draw a line between an event and the next one
            plot_opt = dict(
                line_width = get_optional_scalar("LineWidth") / 4,
                opacity = get_optional_scalar("Opacity"),
                line_color = get_optional_scalar("LineColor"),
                legendgroup = get_optional_scalar("LegendGroup"),
            )

            plots += [go.Scatter(
                name=legend_name,
                x=x, y=y,
                text=text,
                mode="lines",
                hoverlabel={'namelength' :-1},
                **plot_opt,
                hovertemplate='%{text}<extra></extra>'
            )]

            if get_optional_scalar("SkipFromMinMaxDate"):
                continue

            min_date = [min(min_date + [_x for _x in x if _x])]
            max_date = [max(max_date + [_x for _x in x if _x])]

        fig = go.Figure(data=plots)

        duration = (max_date[0] - min_date[0]).total_seconds()
        x_shift = datetime.timedelta(seconds=int(duration*0.035))
        y_shift = len(ordered_lines) * 0.1

        fig.update_layout(title=f"Execution timeline of {user_count} users launching a notebook ", title_x=0.5,)
        fig.update_layout(xaxis_range=[min_date[0] - x_shift, max_date[0] + x_shift])
        fig.update_layout(yaxis_range=[len(ordered_lines) - 1 + y_shift, 0 - y_shift]) # range reverted here
        fig.update_layout(xaxis_title="Timeline (by date)")
        fig.update_yaxes(tickmode='array', ticktext=ordered_lines, tickvals=list(range(len(ordered_lines))))

        fig.update_xaxes(showspikes=True, spikecolor="green", spikesnap="cursor", spikemode="across")

        return fig, ""
