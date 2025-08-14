import pandas as pd
import plotly.express as px

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common


def register():
    CPUPower()


def generateGPUUsageData(entries, _variables, key):
    data = []

    variables = dict(_variables)  # make a copy before modifying

    for entry in entries:
        if not entry.results.cpu_power_usage:
            continue

        entry_name = entry.get_name(variables)
        for gpu_power_usage in entry.results.cpu_power_usage.usage:
            entry_data = dict()
            entry_data["name"] = entry_name
            entry_data["ts"] = gpu_power_usage.ts
            entry_data[key] = gpu_power_usage.__dict__[key]

            data.append(entry_data)

    return data


class CPUPower():
    def __init__(self):
        self.name = "CPU Usage by power"
        self.key = "power_mw"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        entries = common.Matrix.all_records(settings, setting_lists)

        df = pd.DataFrame(generateGPUUsageData(entries, variables, self.key))

        if df.empty:
            return None, "Not data available ..."

        df = df.sort_values(by=["ts", "name"], ascending=False)
        fig = px.line(df, hover_data=df.columns,
                      x="ts", y=self.key, color="name")

        fig.update_yaxes(title=f"{self.key}")

        fig.update_layout(title=self.name, title_x=0.5,)

        return fig, ""
