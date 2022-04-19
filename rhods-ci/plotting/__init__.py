from collections import defaultdict

import plotly.graph_objs as go

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    Plot("Gantt")

class Plot():
    def __init__(self, name):
        self.name = name
        self.id_name = name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, params, param_lists, variables, cfg):

        all_XY = defaultdict(dict)

        for entry in common.Matrix.all_records(params, param_lists):
            for podname, podtime in sorted(entry.results.pod_time.items()):
                idx = podname.split("-")[2]
                name = f"Pod #{int(idx):02d}"

                all_XY["0. pod creation"][name] = (podtime.creation_time - entry.results.job_creation_time).seconds

                all_XY["1. pod scheduling"][name] = (podtime.start_time - podtime.creation_time).seconds
                all_XY["2. container initialization"][name] = (podtime.container_started - podtime.start_time).seconds
                all_XY["3. container execution"][name] = (podtime.container_finished - podtime.container_started).seconds

                pass
        all_XY["-- job execution"]["Job"] = (entry.results.job_completion_time - entry.results.job_creation_time).seconds
        data = []
        for legend_name, XY in sorted(all_XY.items()):
            data += [go.Bar(name=legend_name,
                            y=list(XY.keys()), x=list(XY.values()),
                            hoverlabel={'namelength' :-1},
                            orientation="h")]

        fig = go.Figure(data=data)
        fig.update_layout(barmode='stack', title="Execution timeline of 100 Pods doing a sleep(60s)", title_x=0.5,)
        return fig, ""
