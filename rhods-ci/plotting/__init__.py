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
        info = defaultdict(dict)
        user_count = 0

        for entry in common.Matrix.all_records(params, param_lists):
            for podname, podtime in sorted(entry.results.pod_time.items()):
                user_count += 1

                idx = podname.split("-")[2]
                name = f"User #{idx}"

                all_XY["00. Test pod creation"][name] = (podtime.creation_time - entry.results.job_creation_time).seconds / 60

                all_XY["01. Test pod scheduling"][name] = (podtime.start_time - podtime.creation_time).seconds / 60
                all_XY["02. Test initialization"][name] = (podtime.container_started - podtime.start_time).seconds / 60
                #all_XY["03. Test execution"][name] = (podtime.container_finished - podtime.container_started).seconds / 60

                info[name]["test_container_started"] = podtime.container_started
                info[name]["test_container_finished"] = podtime.container_finished

        for entry in common.Matrix.all_records(params, param_lists):
            for notebook_name, notebook_time in sorted(entry.results.notebook_time.items()):
                name = f"User #{notebook_name.split('-')[2]}".replace("testuser", "")

                all_XY["03. ODS-CI Test initialization"][name] = (notebook_time.creation_time - info[name]["test_container_started"]).seconds / 60

                all_XY["10. Notebook scheduling"][name] = (notebook_time.creation_time - entry.results.notebook_start_time).seconds / 60
                all_XY["11. Notebook preparation"][name] = (notebook_time.pulling - notebook_time.creation_time).seconds / 60
                all_XY["12. Notebook image pull"][name] = (notebook_time.pulled - notebook_time.pulling).seconds / 60
                all_XY["13. Notebook initialization"][name] = (notebook_time.started - notebook_time.pulled).seconds / 60
                all_XY["14. Notebook execution"][name] = (notebook_time.terminated - notebook_time.started).seconds / 60
                all_XY["20. Test termination"][name] = (info[name]["test_container_finished"] - notebook_time.terminated).seconds / 60

        all_XY["-- job execution"]["Job"] = (entry.results.job_completion_time - entry.results.job_creation_time).seconds / 60
        data = []
        for legend_name, XY in sorted(all_XY.items()):
            opacity = 0.9
            if legend_name.startswith("0") or legend_name.startswith("--"):
                opacity = 0.3
            data += [go.Bar(name=legend_name,
                            y=list(XY.keys()), x=list(XY.values()),
                            opacity=opacity,
                            hoverlabel={'namelength' :-1},
                            orientation="h")]

        fig = go.Figure(data=data)

        fig.update_layout(barmode='stack', title=f"Execution timeline of {user_count} users launching a notebook ", title_x=0.5,)
        fig.update_layout(yaxis_title="Notebook username")
        fig.update_layout(xaxis_title="Timeline (in minutes)")
        return fig, ""
