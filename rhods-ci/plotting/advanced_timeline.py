from collections import defaultdict
import datetime

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    Timeline("Timeline2")

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

        if sum(1 for _ in common.Matrix.all_records(params, param_lists)) != 1:
            return {}, "ERROR: only one experiment must be selected"

        def get_text(start_evt, finish_evt, start, finish):
            duration_s = (finish - start).total_seconds()

            if duration_s < 120:
                duration = f"{duration_s:.0f} seconds"
            else:
                duration_min = duration_s / 60
                duration = f"{duration_min:.1f} minutes"

            return f"FROM: {start_evt}<br>TO: {finish_evt}<br>{duration}"

        data = []
        for entry in common.Matrix.all_records(params, param_lists):
            user_count = len(entry.results.test_pods)
            test_nodes = {}
            rhods_nodes = {}

            test_nodes_index = list(entry.results.testpod_hostnames.values()).index
            rhods_nodes_index = list(entry.results.notebook_hostnames.values()).index

            for testpod_name, nodename in entry.results.testpod_hostnames.items():
                user_idx = int(testpod_name.split("-")[2])
                test_nodes[user_idx] = f"Test node #{test_nodes_index(nodename)}"

            for notebook_name, nodename in entry.results.notebook_hostnames.items():
                user_idx = int(notebook_name.replace("jupyterhub-nb-testuser", ""))
                rhods_nodes[user_idx] = f"RHODS node #{rhods_nodes_index(nodename)}"

            def get_line_name(user_idx):
                user_name = f"User #{user_idx}"

                test_node = test_nodes[user_idx]
                rhods_node = rhods_nodes.get(user_idx, "<no RHODS node>")

                return user_name + "<br>" + test_node + "<br>" + rhods_node

            for testpod_name in entry.results.test_pods:
                user_idx = int(testpod_name.split("-")[2])

                pod_times = entry.results.pod_times[testpod_name]
                event_times = entry.results.event_times[testpod_name]

                def generate_data(LegendName, start_evt, finish_evt, **kwargs):
                    defaults = dict(
                        LegendName=LegendName,
                        LegendGroup="Test Pod",
                        Start=kwargs.get("Start") or data[-1]["Finish"],
                        Finish=kwargs["Finish"],
                        LineName=get_line_name(user_idx),
                        Opacity=0.5,
                        LineWidth=50,
                        LineSortIndex=kwargs["Finish"],
                    )

                    defaults["Text"] = get_text(start_evt, finish_evt, defaults["Start"], defaults["Finish"])

                    return defaults | kwargs

                data.append(generate_data("01. Test pod scheduling",
                                          "Job creation", "Pod scheduled",
                                          Finish=event_times.scheduled,
                                          Start=entry.results.job_creation_time,))
                data.append(generate_data("02. Test pod preparation",
                                          "Pod scheduled", "pulling image",
                                          Finish=event_times.pulling))
                data.append(generate_data("03. Test pod image pull",
                                          "Pod pulling image", "image pulled",
                                          Finish=event_times.pulled))
                data.append(generate_data("04. Test pod initialization",
                                          "Pod image pulled", "container started",
                                          Finish=pod_times.container_started))
                data.append(generate_data("05. Test Execution",
                                          "Container started", "container finished",
                                          Finish=pod_times.container_finished))

                info[user_idx]["test_container_started"] = pod_times.container_started


        for entry in common.Matrix.all_records(params, param_lists):
            for notebook_name in entry.results.notebook_pods:
                user_idx = int(notebook_name.replace("jupyterhub-nb-testuser", ""))

                pod_times = entry.results.pod_times[notebook_name]
                event_times = entry.results.event_times[notebook_name]

                def generate_data(task_name, start_evt, finish_evt, **kwargs):
                    defaults = dict(
                        Start=kwargs.get("Start") or data[-1]["Finish"],
                        Finish=kwargs["Finish"],
                        LegendName=task_name,
                        LegendGroup="Notebook",
                        Opacity=1,
                        LineName=get_line_name(user_idx),
                        LineWidth=100,
                        LineSortIndex=kwargs["Finish"],
                    )

                    defaults["Text"] = get_text(start_evt, finish_evt, defaults["Start"], defaults["Finish"])

                    return defaults | kwargs

                data.append(
                    generate_data(
                        "10. ODS-CI Test initialization",
                        "Test container started", "Notebook pod appeared",
                        Start=info[user_idx]["test_container_started"],
                        Finish=event_times.appears_time,
                        LineWidth=60,
                        LegendGroup="ODS CI"
                    )
                )

                data.append(generate_data(
                    "20. Notebook scheduling",
                    "Notebook pod appeared", "scheduled",
                    Finish=event_times.scheduled))
                data.append(generate_data(
                    "21. Notebook preparation",
                    "Notebook pod cheduled", "image pulling",
                    Finish=event_times.pulling))
                data.append(generate_data(
                    "22. Notebook image pull",
                    "Notebook image pulling", "image pulled",
                    Finish=event_times.pulled))
                data.append(generate_data(
                    "23. Notebook initialization",
                    "Notebook image pulled", "container started",
                    Finish=event_times.started))
                data.append(generate_data(
                    "24. Notebook execution",
                    "Notebook container started", "container terminated",
                    Finish=event_times.terminated))

                if "failedScheduling" in event_times.__dict__:
                    data.append(generate_data(
                        "Warnings",
                        "Failed Scheduling", event_times.failedScheduling[2],
                        Start=event_times.failedScheduling[0],
                        Finish=event_times.failedScheduling[1],
                        LineColor="Red",
                        LineWidth=80,
                        Opacity=0.9,
                    ))


        data.insert(0, dict(
            LegendName="Test job lifespan",
            Start=entry.results.job_creation_time,
            Finish=entry.results.job_completion_time,
            Opacity=1,
            Text="Test job lifespan",
            LineName="Test Job",
            LineWidth=100,
        ))

        # ---

        plots = []
        df = pd.DataFrame(data)
        LINE_SORT_LEGENT_NAME = "05. Test Execution"

        ordered_lines = list(df[df["LegendName"] == LINE_SORT_LEGENT_NAME].sort_values("LineSortIndex")["LineName"].unique())
        for line_name in df["LineName"].unique():
            if line_name in ordered_lines:
                continue
            ordered_lines.append(line_name)

        min_date = []
        max_date = []
        for legend_name in df["LegendName"].unique():
            rows = df[df["LegendName"] == legend_name]

            x = []
            y = []
            text = []
            for row in range(len(rows)):
                line_idx = ordered_lines.index(rows["LineName"].values[row])

                get_ts = lambda name: datetime.datetime.fromtimestamp(int(rows[name].values[row].astype(datetime.datetime))/1000000000)
                x += [get_ts("Start"), get_ts("Finish"), None]
                y += [line_idx, line_idx, None]
                # The None value tells Plotly not to connect this pair ^^^ with the next one

            def get_optional_scalar(column_name):
                return None if rows[column_name].isnull().values[0] \
                    else rows[column_name].values[0]

            plot_opt = dict(
                line_width = get_optional_scalar("LineWidth"),
                opacity = get_optional_scalar("Opacity"),
                line_color = get_optional_scalar("LineColor"),
                legendgroup = get_optional_scalar("LegendGroup"),
                text = get_optional_scalar("Text"),
            )

            plots += [go.Scatter(
                name=legend_name,
                x=x, y=y,
                mode="lines",
                hoverlabel={'namelength' :-1},
                **plot_opt,
            )]

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

        return fig, ""
