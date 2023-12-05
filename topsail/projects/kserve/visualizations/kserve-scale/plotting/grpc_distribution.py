from collections import defaultdict

import statistics as stats

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    GrpcCallsDistribution()

def generateGrpcCallsDistribution(entry):
    data = []
    for user_idx, user_data in entry.results.user_data.items():
        if not user_data: continue

        previous_step_time = entry.results.test_start_end_time.start

        for grpc_call in user_data.grpc_calls:
            data.append(dict(
                Name = f"{grpc_call.name}",
                Duration = grpc_call.duration.total_seconds(),
                Isvc = grpc_call.isvc,
                Attempts = grpc_call.attempts,
            ))

    return data

class GrpcCallsDistribution():
    def __init__(self):
        self.name = "GRPC calls distribution"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):

        cnt = common.Matrix.count_records(settings, setting_lists)
        if cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {cnt}."

        cfg__show_attempts = cfg.get("show_attempts", False)

        for entry in common.Matrix.all_records(settings, setting_lists):
            break

        data = generateGrpcCallsDistribution(entry)

        if not data:
            return None, "No data to plot ..."

        df = pd.DataFrame(data)


        fig = px.histogram(df, x="Attempts" if cfg__show_attempts else "Duration",
                           color="Name",
                           marginal="box",
                           barmode="overlay",
                           hover_data=df.columns)
        if cfg__show_attempts:
            fig.update_layout(xaxis_title="Number of attemps before the GRPC calls succeeds")
            title = f"Distribution of the number of attemps before the GRPC calls succeeds"
        else:
            fig.update_layout(xaxis_title="Duration of the GRPC calls")
            title = f"Distribution of the duration of the GRPC calls"

        fig.update_layout(title=title, title_x=0.5)

        msg = []
        if len(df) >= 2 and not cfg__show_attempts:
            q1, med, q3 = stats.quantiles(df.Duration)
            q90 = stats.quantiles(df.Duration, n=10)[8] # 90th percentile
            q100 = df.Duration.max()

            def time(sec):
                if sec < 0.001:
                    return f"0 seconds"
                elif sec < 5:
                    return f"{sec:.3f} seconds"
                if sec < 20:
                    return f"{sec:.1f} seconds"
                elif sec <= 120:
                    return f"{sec:.0f} seconds"
                else:
                    return f"{sec/60:.1f} minutes"

            msg += [f"{len(df)} GRPC calls were performed."]
            msg.append(html.Br())
            msg += [f"It took them ", html.B(f"between {time(df.Duration.min())} and {time(df.Duration.max())}"), " to complete."]
            msg.append(html.Br())
            msg.append(f"25% completed in less than {time(q1)} [Q1]")
            msg.append(html.Br())
            msg.append(f"50% completed in less than {time(med)} (+ {time(med-q1)}) [median]")
            msg.append(html.Br())
            msg.append(f"75% completed in less than {time(q3)} (+ {time(q3-med)}) [Q3]")
            msg.append(html.Br())
            msg.append(f"90% completed in less than {time(q90)} (+ {time(q90-q3)}) [90th quantile]")
            msg.append(html.Br())
            msg.append(f"There are {time(q3 - q1)} between Q1 and Q3.")
            msg.append(html.Br())
            msg.append(f"There are {time(q100 - q3)} between Q3 and Q4.")
            msg.append(html.Br())

        return fig, msg
