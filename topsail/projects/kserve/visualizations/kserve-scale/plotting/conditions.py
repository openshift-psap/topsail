from collections import defaultdict
import re
import logging
import datetime
import math
import copy

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common


def register():
    ConditionsTimeline()
    ConditionsInStateTimeline()
    IntervalBetweenCreations()


def generateCreationData(entry, kind):
    data = []
    for user_idx, user_data in entry.results.user_data.items():
        if not user_data.resource_times: continue

        previous_creation = None
        for resource_name, resource_times in sorted(user_data.resource_times.items(), key=lambda kv:kv[1].model_id):
            owner = f"User {resource_times.user_idx:03d}"

            if kind and resource_times.kind != kind: continue

            if not previous_creation:
                previous_creation = resource_times.creation
                continue

            data.append(dict(
                Owner=owner,
                Duration_s=(resource_times.creation - previous_creation).total_seconds(),
                Model=f"Model {resource_times.model_id:03d}",
                Previous=previous_creation,
                Current=resource_times.creation,
            ))

            previous_creation = resource_times.creation

    return data


def generateConditionsTimeline(entry, kind, user_in_owner=False, user_in_state=False):
    data = []
    for user_idx, user_data in entry.results.user_data.items():
        if not user_data.resource_times: continue

        for resource_name, resource_times in user_data.resource_times.items():
            if kind and resource_times.kind != kind: continue
            if not hasattr(resource_times, "conditions"): continue

            owner = f"Model {resource_times.model_id:03d}"
            if user_in_owner:
                owner = f"{owner} | User {resource_times.user_idx:03d}"

            state = f"{(resource_times.kind + '/') if not kind else ''}Creation"
            if user_in_state:
                state = f"User {resource_times.user_idx:03d} | {state}"

            data.append(dict(
                Owner=owner,
                State=state,
                Time=resource_times.creation,
                Duration_s=0,
                Model=f"Model {resource_times.model_id}",
                Action="Creation",
            ))

            for condition_name, condition_ts in resource_times.conditions.items():
                state = f"{(resource_times.kind + '/') if not kind else ''}{condition_name}"
                if user_in_state:
                    state = f"User {resource_times.user_idx:03d} | {state}"

                data.append(dict(
                    Owner=owner,
                    State=state,
                    Time=condition_ts,
                    Duration_s=(condition_ts - resource_times.creation).total_seconds(),
                    Model=f"Model {resource_times.model_id}",
                    Action=condition_name,
                ))

    return data


class ConditionsTimeline():
    def __init__(self):
        self.name = "Conditions Timeline"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if common.Matrix.count_records(settings, setting_lists) != 1:
            return {}, "ERROR: only one experiment must be selected"

        cfg__kind = cfg.get("kind", "InferenceService")

        for entry in common.Matrix.all_records(settings, setting_lists):
            pass


        df = pd.DataFrame(generateConditionsTimeline(entry, cfg__kind, user_in_state=True))
        df = df.sort_values(by=["Owner", "State"])

        if df.empty:
            return None, "Not data available ..."

        fig = px.line(df, hover_data=df.columns,
                      x="Time", y="Owner", color="State")

        for i in range(len(fig.data)):
            fig.data[i].update(mode='markers+lines')

        fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
        fig.update_layout(barmode='stack')

        fig.update_layout(title=f"Timeline of the <b>{cfg__kind}</b> conditions <br>reaching their <i>Ready</i> state", title_x=0.5,)
        fig.update_layout(yaxis_title="")
        fig.update_layout(xaxis_title="Timeline (by date)")

        return fig, ""


class ConditionsInStateTimeline():
    def __init__(self):
        self.name = "Conditions in State Timeline"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if common.Matrix.count_records(settings, setting_lists) != 1:
            return {}, "ERROR: only one experiment must be selected"

        cfg__kind = cfg.get("kind", None)

        for entry in common.Matrix.all_records(settings, setting_lists):
            src_data = generateConditionsTimeline(entry, cfg__kind, user_in_owner=True)

        if not src_data:
            return None, "Not data available ..."

        df = pd.DataFrame(src_data).sort_values(by=["Owner", "State"])
        df = df[df.Action != "Creation"]

        fig = px.histogram(df, hover_data=df.columns,
                           x="State", y="Duration_s",
                           color="Owner",
                           barmode="group"
                      )

        fig.update_layout(title=f"Time to reach the <b>{cfg__kind}</b> conditions", title_x=0.5,)
        fig.update_layout(yaxis_title="Time to reach condition")
        fig.update_layout(xaxis_title=f"{cfg__kind} condition name")

        return fig, ""


class IntervalBetweenCreations():
    def __init__(self):
        self.name = "Interval Between Creations"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        if common.Matrix.count_records(settings, setting_lists) != 1:
            return {}, "ERROR: only one experiment must be selected"

        cfg__kind = cfg.get("kind", "InferenceService")

        for entry in common.Matrix.all_records(settings, setting_lists):
            src_data = generateCreationData(entry, cfg__kind)

        if not src_data:
            return None, "Not data available ..."

        df = pd.DataFrame(src_data)
        df = df.sort_values(by=["Model"])

        fig = px.bar(df, hover_data=df.columns,
                     x="Model", y="Duration_s",
                     color="Owner",
                     barmode="group"
                     )

        fig.update_layout(title=f"Time between the models creations", title_x=0.5,)
        fig.update_layout(yaxis_title="Time between models creation (in seconds)")
        fig.update_layout(xaxis_title=f"Model name")

        return fig, ""
