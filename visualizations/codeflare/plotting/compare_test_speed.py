from collections import defaultdict
import re
import logging
import datetime
import math
import copy

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common


def register():
    CompareTestSpeed()

class CompareTestSpeed():
    def __init__(self):
        self.name = "Compare Test Speed"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        if len(variables) != 1:
            return None, f"{self.name} only works with one variable. Got {len(variables)}: {', '.join(variables)}"

        variable = list(variables)[0]

        text = []

        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):

            test_duration = (entry.results.test_start_end_time.end - entry.results.test_start_end_time.start).total_seconds() / 60
            processing_speed = entry.results.test_case_properties.total_pod_count / test_duration

            test_cfg_setting = entry.settings.__dict__[variable]

            launch_speed = entry.results.test_case_properties.total_pod_count/entry.results.test_case_properties.launch_duration
            data.append(dict(
                speed = launch_speed,
                what = "Launch speed",
            ))
            data[-1][variable] = test_cfg_setting

            data.append(dict(
                what = "Processing speed",
                speed = processing_speed,
            ))
            data[-1][variable] = test_cfg_setting

            text += [html.Code(f"{variable}={test_cfg_setting} | Launch speed: {launch_speed:.2f} Pods/minute | Test speed: {processing_speed:.2f} Pods/minute"), html.Br()]

        df = pd.DataFrame(data)
        fig = px.line(df, x=variable, y="speed", color="what", markers=True)

        fig.update_layout(title=f"Comparison of the processing speed<br>over different {variable} values", title_x=0.5,)
        fig.update_layout(yaxis_title="Processing speed, in Pod/minutes")
        fig.update_layout(xaxis_title=variable)

        return fig, html.P(text)
