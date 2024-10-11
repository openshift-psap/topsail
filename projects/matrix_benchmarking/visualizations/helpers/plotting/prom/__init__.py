import datetime
from collections import defaultdict

import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def default_get_metrics(entry, metric):
    return entry.results.metrics[metric]

def get_tests_timestamp_plots(entries, y_max, variables):
    data = []
    tests_timestamp_y_position = [-y_max*0.25] * 3

    now = datetime.datetime.now()
    tz_offset = datetime.datetime.fromtimestamp(now.timestamp()) - datetime.datetime.utcfromtimestamp(now.timestamp())

    for entry in entries:
        if "tests_timestamp" not in entry.results.__dict__: continue

        for test_timestamp in entry.results.tests_timestamp:
            # convert to local timezone and remove timezone info
            start = test_timestamp.start + tz_offset; start.replace(tzinfo=None)
            end = test_timestamp.end + tz_offset; end.replace(tzinfo=None)

            settings_text_lst = [str(v) if k.startswith("*") else f"{k}={v}" for k, v in test_timestamp.settings.items() if k in variables]
            if not settings_text_lst:
                settings_text_lst = [str(v) if k.startswith("*") else f"{k}={v}" for k, v in test_timestamp.settings.items()]

            mid = start + (end-start) / 2
            data.append(
                go.Scatter(
                    x=[start, mid, end],
                    y=tests_timestamp_y_position,
                    name="Test timestamps",
                    hoverlabel={'namelength' :-1},
                    hovertext="<br>".join(f"{k}={v}" for k, v in test_timestamp.settings.items()),
                    legendgroup="Test timestamps",
                    legendgrouptitle_text="Test timestamps",
                    text=["", "<br>".join(settings_text_lst) + "<br>",""],
                    mode='lines+text',
                    textposition="top center",
                    showlegend=False,
                    line=dict(width=15),
                ))

    return tests_timestamp_y_position[0], data


class Plot():
    def __init__(self, metrics, name, title, y_title,
                 get_metrics=default_get_metrics,
                 filter_metrics=lambda entry, metrics: metrics,
                 as_timestamp=False,
                 get_legend_name=None,
                 show_metrics_in_title=False,
                 show_queries_in_title=False,
                 show_legend=True,
                 y_divisor=1,
                 higher_better=False,
                 ):
        self.name = name
        self.id_name = f"prom_overview_{''.join( c for c in self.name if c not in '?:!/;()' ).replace(' ', '_').lower()}"
        self.title = title
        self.metrics = metrics
        self.y_title = y_title
        self.y_divisor = y_divisor
        self.filter_metrics = filter_metrics
        self.get_metrics = get_metrics
        self.as_timestamp = as_timestamp
        self.get_legend_name = get_legend_name
        self.show_metrics_in_title = show_metrics_in_title
        self.show_queries_in_title = show_queries_in_title
        self.show_legend = show_legend
        self.higher_better = higher_better

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        plot_title = self.title if self.title else self.name

        cfg__as_timeline = cfg.get("as_timeline", False)

        if self.show_metrics_in_title:
            metric_names = [
                list(metric.items())[0][0] if isinstance(metric, dict) else metric
                for metric in self.metrics.keys()
            ]
            plot_title += f"<br>{'<br>'.join(metric_names)}"

        if self.show_queries_in_title:
            queries_names = self.metrics.values()
            plot_title += f"<br>{'<br>'.join(queries_names)}"

        y_max = 0
        single_expe = common.Matrix.count_records(settings, setting_lists) == 1
        as_timeline = single_expe or cfg__as_timeline

        show_test_timestamps = True
        if not as_timeline:
            show_test_timestamps = False

        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            entry_name = entry.get_name(variables)

            sort_index = entry.get_settings()[ordered_vars[0]] if len(variables) == 1 \
                else entry_name

            for _metric in self.metrics:
                metric_name, metric_query = list(_metric.items())[0] if isinstance(_metric, dict) else (_metric, _metric)

                for metric in self.filter_metrics(entry, self.get_metrics(entry, metric_name)):
                    if not metric: continue

                    x_values = [x for x, y in metric.values.items()]
                    y_values = [y/self.y_divisor for x, y in metric.values.items()]

                    if self.get_legend_name:
                        legend_name, legend_group = self.get_legend_name(metric_name, metric.metric)
                    else:
                        legend_name = metric.metric.get("__name__", metric_name)
                        legend_group = None

                    if as_timeline:
                        if legend_group is None:
                            legend_group = ""
                        else:
                            legend_group += "<br>"
                        legend_group += entry.get_name(variables)

                    if legend_group: legend_group = str(legend_group)
                    else: legend_group = None

                    if self.as_timestamp:
                        x_values = [datetime.datetime.fromtimestamp(x) for x in x_values]
                    else:
                        x_start = x_values[0]
                        x_values = [x-x_start for x in x_values]

                    y_max = max([y_max]+y_values)
                    if as_timeline:
                        data.append(
                            go.Scatter(
                                x=x_values, y=y_values,
                                name=str(legend_name),
                                hoverlabel= {'namelength' :-1},
                                showlegend=self.show_legend,
                                legendgroup=legend_group,
                                legendgrouptitle_text=legend_group,
                                mode='markers+lines'))

                    else:
                        entry_version = entry.get_name(variables)
                        for y_value in y_values:
                            data.append(dict(Version=entry_version,
                                             SortIndex=sort_index,
                                             Metric=legend_name,
                                             Value=y_value))

        if not data:
            return None, "No metric to plot ..."

        if show_test_timestamps:
            tests_timestamp_y_position, plots = get_tests_timestamp_plots(common.Matrix.all_records(settings, setting_lists), y_max, variables)
            data += plots

        if as_timeline:
            fig = go.Figure(data=data)

            fig.update_layout(
                title=plot_title, title_x=0.5,
                yaxis=dict(title=self.y_title, range=[tests_timestamp_y_position if show_test_timestamps else 0, y_max*1.05]),
                xaxis=dict(title=None if self.as_timestamp else "Time (in s)"))
        else:
            df = pd.DataFrame(data).sort_values(by=["SortIndex"])
            fig = px.box(df, x="Version", y="Value", color="Version", points="all")
            fig.update_layout(
                title=plot_title, title_x=0.5,
                yaxis=dict(title=self.y_title)
            )

        msg = []

        return fig, msg
