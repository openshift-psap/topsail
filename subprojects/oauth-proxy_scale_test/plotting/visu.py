import logging

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

class Visualize():
    def __init__(self):
        self.name = "Oauth-proxy scale test"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        data = []
        for entry in common.Matrix.all_records(settings, setting_lists):
            cpu_values = None
            if entry.settings.host == "nginx":
                cpu_values_key = "cluster__container__cpu__namespace=oauth-proxy_pod=nginx-deployment.*_container=nginx"
            elif entry.settings.host == "oauth-proxy":
                cpu_values_key = "cluster__container__cpu__namespace=oauth-proxy_pod=oauth-proxy-example.*_container=oauth-proxy"
            else:
                logging.error(f"Unknown host type: {entry.settings.host}")
                continue

            endpoint = "<br>".join([f"{k}={entry.settings.__dict__[k]}" for k in ordered_vars])
            logging.info(f"Endpoint --> {endpoint}")
            cpu_metrics = entry.results.metrics["cluster"][cpu_values_key]
            if not cpu_metrics:
                logging.info(f"{cpu_values_key} ==> Empty :/")
                continue

            cpu_values = [float(value) for ts, value in cpu_metrics[0]["values"]]

            for cpu_value in cpu_values:
                data.append(dict(
                    Endpoint=endpoint,
                    CPU=cpu_value,
                    Host=entry.settings.host,
            ))

        df = pd.DataFrame(data)
        df = df.sort_values(by=["Endpoint"])

        if df.empty:
            return None, "Nothing to plot (no data)"

        fig = px.box(df, x="Endpoint", y="CPU", color="Host", title=self.name)

        fig.update_layout(title_x=0.5,)
        fig.update_layout(xaxis_title="")
        fig.update_layout(yaxis_title="CPU usage for the different endpoints")
        return fig, ""
