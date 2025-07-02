import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common


def register():
    MetricUsage(CPUUsage=True, NetworkUsage=False, DiskUsage=False)
    MetricUsage(CPUUsage=False, NetworkUsage=True, DiskUsage=False)
    MetricUsage(CPUUsage=False, NetworkUsage=False, DiskUsage=True)


def generateUsageData(entries, _variables, main_key, secondary_key):
    data = []

    variables = dict(_variables)  # make a copy before modifying

    for entry in entries:
        main_field = entry.results.__dict__.get(main_key)
        if not main_field:
            continue

        entry_name = entry.get_name(variables)
        interval = main_field.interval
        t = 0
        for hw_usage in main_field.__dict__[secondary_key]:
            entry_data = dict()
            entry_data["name"] = entry_name
            entry_data["ts"] = t
            entry_data[secondary_key] = hw_usage

            t += interval
            data.append(entry_data)

    return data


class MetricUsage():
    def __init__(self, CPUUsage=True, NetworkUsage=False, DiskUsage=False):
        self.name = "System"
        if NetworkUsage:
            self.name += " Network Usage"
            self.key = "network"
        elif DiskUsage:
            self.name += " Disk Usage"
            self.key = "disk"
        elif CPUUsage:
            self.name += " CPU Usage"
            self.key = "cpu"
        else:
            raise ValueError("No flavor selected ...")

        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateUsageData(entries, variables, "metrics", self.key))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["ts", "name"], ascending=False)
        fig = px.line(df, hover_data=df.columns,
                      x="ts", y=self.key, color="name")

        fig.update_yaxes(title=f"{self.key}")

        fig.update_layout(title=self.name, title_x=0.5,)

        return fig, ""
