import datetime
import statistics as stats
from collections import defaultdict

import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from . import get_tests_timestamp_plots

def default_get_metrics(entry, metric):
    return entry.results.metrics[metric]


class Plot():
    def __init__(self, metrics, y_title,
                 get_metrics=default_get_metrics,
                 filter_metrics=lambda entry, metrics: metrics,
                 as_timestamp=False,
                 container_name="all",
                 is_memory=False,
                 is_cluster=False,
                 skip_nodes=None,
                 ):

        self.name = f"Prom: {y_title}"

        self.id_name = f"prom_overview_{y_title}"
        self.metrics = metrics
        self.y_title = y_title
        self.filter_metrics = filter_metrics
        self.get_metrics = get_metrics
        self.as_timestamp = as_timestamp
        self.container_name = container_name
        self.is_memory = is_memory
        self.is_cluster = is_cluster

        if skip_nodes is not None:
            self.skip_nodes = skip_nodes
        else:
            self.skip_nodes = self.is_memory and not self.is_cluster

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        cfg__as_timeline = cfg.get("as_timeline", False)

        fig = go.Figure()
        metric_names = [
            list(metric.items())[0][0] if isinstance(metric, dict) else metric
            for metric in self.metrics
        ]

        plot_title = f"Prometheus: {self.y_title}"
        y_max = 0

        y_divisor = 1024*1024*1024 if self.is_memory else 1

        single_expe = common.Matrix.count_records(settings, setting_lists) == 1

        as_timeline = single_expe or cfg__as_timeline

        show_test_timestamps = True
        if not as_timeline:
            show_test_timestamps = False

        data = []
        data_rq = []
        data_lm = []

        for entry in common.Matrix.all_records(settings, setting_lists):
            entry_name = entry.get_name(variables)

            sort_index = entry.get_settings()[ordered_vars[0]] if len(variables) == 1 \
                else entry_name

            for _metric in self.metrics:
                metric_name, metric_query = list(_metric.items())[0] if isinstance(_metric, dict) else (_metric, _metric)

                for metric in self.filter_metrics(entry, self.get_metrics(entry, metric_name)):
                    if not metric: continue

                    x_values = [x for x, y in metric.values.items()]
                    y_values = [y/y_divisor for x, y in metric.values.items()]

                    metric_actual_name = metric.metric.get("__name__", metric_name)
                    legend_name = metric_actual_name
                    if metric.metric.get("container") == "POD": continue

                    if "_sum_" in metric_name:
                        legend_group = None
                        legend_name = "sum(all)"
                    else:
                        legend_group = metric.metric.get("pod", "<no podname>") + "/" + metric.metric.get("container", self.container_name) \
                            if not self.is_cluster else None

                    if self.as_timestamp:
                        x_values = [datetime.datetime.fromtimestamp(x) for x in x_values]
                    else:
                        x_start = x_values[0]
                        x_values = [x-x_start for x in x_values]

                    y_max = max([y_max]+y_values)

                    opts = {}

                    if self.skip_nodes and "node" not in metric.metric:
                        continue

                    is_req_or_lim = "limit" in legend_name or "requests" in legend_name

                    if as_timeline:
                        entry_name = "Test"

                        if "requests" in metric_actual_name:
                            opts["line_color"] = "orange"
                            opts["line_dash"] = "dot"
                            opts["mode"] = "lines"

                        elif "limits" in metric_actual_name or "capacity" in metric_actual_name:
                            opts["line_color"] = "red"
                            opts["mode"] = "lines"
                            opts["line_dash"] = "dash"
                        else:
                            opts["mode"] = "markers+lines"

                        data.append(
                            go.Scatter(x=x_values, y=y_values,
                                       name=legend_name,
                                       hoverlabel= {'namelength' :-1},
                                       showlegend=True,
                                       legendgroup=legend_group,
                                       legendgrouptitle_text=legend_group,
                                       **opts))

                    else:
                        if is_req_or_lim:
                            lst = data_lm if "limits" in legend_name else data_rq

                            lst.append(dict(Version=entry_name,
                                            SortIndex=sort_index,
                                            Value=y_values[0],
                                            Metric=legend_name))

                        else:
                            for y_value in y_values:
                                data.append(dict(Version=entry_name,
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
                yaxis=dict(title=self.y_title + (" (in Gi)" if self.is_memory else ""), range=[tests_timestamp_y_position if show_test_timestamps else 0, y_max*1.05]),
                xaxis=dict(title=f"Time (in s)"))
        else:
            df = pd.DataFrame(data).sort_values(by=["SortIndex"])

            fig = px.box(df, x="Version", y="Value", color="Version")
            fig.update_layout(
                title=plot_title, title_x=0.5,
                yaxis=dict(title=self.y_title + (" (in Gi)" if self.is_memory else ""))
            )
            if data_rq:
                df_rq = pd.DataFrame(data_rq).sort_values(by=["SortIndex"])
                fig.add_scatter(name="Request",
                                x=df_rq['Version'], y=df_rq['Value'], mode='lines',
                                line=dict(color='orange', width=5, dash='dot'))
            if data_lm:
                df_lm = pd.DataFrame(data_lm).sort_values(by=["SortIndex"])
                fig.add_scatter(name="Limit",
                                x=df_lm['Version'], y=df_lm['Value'], mode='lines',
                                line=dict(color='red', width=5, dash='dot'))

        msg = []
        return fig, msg
