from collections import defaultdict
import datetime
import math

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
import plotly.subplots

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from .. import store as rhodsci_store

from . import timeline_data

def register():
    Completion("Price to completion")

class Completion():
    def __init__(self, name):
        self.name = name
        self.id_name = name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        user_count = cfg.get("timeline.users", 20)

        if "notebook_size" in ordered_vars:
            return {}, "Please select a notebook size"

        if "notebook_size" not in settings:
            return {}, "Cannot plot, 'notebook_size' setting not available."

        notebook_size = settings["notebook_size"]
        del settings["notebook_size"]

        cpu_needed = rhodsci_store.NOTEBOOK_REQUESTS[notebook_size].cpu * user_count
        memory_needed = rhodsci_store.NOTEBOOK_REQUESTS[notebook_size].memory * user_count

        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):

            instance_count = max([math.ceil(memory_needed / entry.results.memory),
                                  math.ceil(cpu_needed / entry.results.cpu)])


            time = 1 # hr
            price = time * entry.results.price/60 * instance_count

            data.append(dict(instance=f"{entry.results.group} - {instance_count}x {entry.import_settings['instance']}",
                             price=price, time=time, instance_count=instance_count))
        if not data:
            return {}, "no entry could be found ..."

        df = pd.DataFrame(data)
        fig = plotly.subplots.make_subplots(specs=[[{"secondary_y": True}]])
        for legend_name in ["price"]:

            fig.add_trace(
                go.Bar(
                    name="Instance count",
                    x=df["instance"], y=df["instance_count"],
                    hoverlabel={'namelength' :-1},
                    opacity=0.5,
                    ), secondary_y=True)

            fig.add_trace(
                go.Scatter(
                    name="Total hourly price",
                    x=df["instance"], y=df[legend_name],
                    mode="lines",
                hoverlabel={'namelength' :-1},
                ))


        fig.update_yaxes(title_text="<b>Price to completion</b> (in $ per hour, lower is better)")
        fig.update_yaxes(title_text="Number of instances required", secondary_y=True)
        fig.update_layout(title=f"Price per instance type<br>to run {user_count} {notebook_size} notebooks",
                          title_x=0.5)
        return fig, ""
