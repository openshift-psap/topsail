from collections import defaultdict
import datetime
import math
import logging

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px
import plotly.subplots

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

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
        cnt = common.Matrix.count_records(settings, setting_lists)
        if cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            break

        user_count = cfg.get("user_count", entry.results.user_count)

        mode = cfg.get("mode", None)

        if mode == "notebooks":
            rq_cpu = entry.results.odh_dashboard_config.notebook_request_size_cpu
            rq_mem = entry.results.odh_dashboard_config.notebook_request_size_mem

        elif mode == "test_pods":
            rq_cpu = entry.results.tester_job.request.cpu
            rq_mem = entry.results.tester_job.request.mem
        else:
            mode = "pods"
            rq_cpu = float(cfg.get("notebook_cpu", 1))
            rq_mem = float(cfg.get("notebook_mem", 1))

        if not (rq_mem and rq_mem):
            return {}, f"no request could be found for mode {mode} ... ({rq_cpu=}, {rq_mem=})"

        cpu_needed = rq_cpu * user_count
        memory_needed = rq_mem * user_count

        machines_in_use = set()
        unknown_hostnames = set([None])
        for hostname in entry.results.notebook_hostnames.values():
            try:
                machines_in_use.add(entry.results.nodes_info[hostname].instance_type)
            except KeyError as e:
                if hostname not in unknown_hostnames:
                    logging.warning(f"completion: hostname={hostname} not found ...")
                    unknown_hostnames.add(hostname)
            except AttributeError as e:
                logging.warning(f"completion: {e} ...")

        data = []
        has_price = False
        for machine_entry in entry.results.possible_machines:
            instance_count = max([math.ceil(memory_needed / machine_entry.memory),
                                  math.ceil(cpu_needed / machine_entry.cpu)])

            time = 1 # hr
            price = time * machine_entry.price * instance_count
            if price: has_price = True
            machine_in_use = machine_entry.instance_name in machines_in_use

            data.append(dict(instance=f"{instance_count} x {machine_entry.instance_name} ({machine_entry.group})",
                             price=price, time=time, instance_count=instance_count, machine_in_use=machine_in_use))

        if not data:
            return {}, "no entry could be found ..."

        df = pd.DataFrame(data)
        fig = plotly.subplots.make_subplots(specs=[[{"secondary_y": True}]])
        for legend_name in ["price"]:
            df_in_use = df[df["machine_in_use"] == True]
            df_not_in_use = df[df["machine_in_use"] == False]
            fig.add_trace(
                go.Bar(
                    name="Instance count",
                    x=df_not_in_use["instance"], y=df_not_in_use["instance_count"],
                    hoverlabel={'namelength' :-1},
                    opacity=0.5,
                    ), secondary_y=True if has_price else False)

            fig.add_trace(
                go.Bar(
                    name="Instance count (used in this run)",
                    x=df_in_use["instance"], y=df_in_use["instance_count"],
                    hoverlabel={'namelength' :-1},
                    opacity=0.5,
                    ), secondary_y=True if has_price else False)
            if not has_price: continue
            fig.add_trace(
                go.Scatter(
                    name="Total hourly price",
                    x=df["instance"], y=df[legend_name],
                    mode="lines",
                hoverlabel={'namelength' :-1},
                ))


        if has_price:
            fig.update_yaxes(title_text="<b>Price to completion</b> (in $ per hour, lower is better)")

        fig.update_yaxes(title_text="Number of instances required", secondary_y=True if has_price else False)
        fig.update_layout(title=f"Price per instance type<br>to run {user_count} {mode.replace('_', ' ')}<br>with cpu={rq_cpu}, mem={rq_mem:.2f}Gi",
                          title_x=0.5)
        return fig, ""
