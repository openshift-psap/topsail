import pandas as pd
import plotly.graph_objects as go
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
        if not hasattr(main_field, secondary_key):
            continue
        if secondary_key == "network":
            mb_s_sent = [(item / (1024 * 1024)) / interval for item in main_field.network.get("send", [])]
            mb_s_recv = [(item / (1024 * 1024)) / interval for item in main_field.network.get("recv", [])]
            net_time_points = [i * interval for i in range(len(main_field.network.get("send", [])))]
            for send, recv, t in zip(mb_s_sent, mb_s_recv, net_time_points):
                entry_data = {
                    "name": entry_name,
                    "ts": t,
                    "send": send,
                    "recv": recv
                }
                data.append(entry_data)
        elif secondary_key == "disk":
            read_mb_s = [(item / (1024 * 1024)) / interval for item in main_field.disk.get("read", [])]
            write_mb_s = [(item / (1024 * 1024)) / interval for item in main_field.disk.get("write", [])]
            disk_time_points = [i * interval for i in range(len(main_field.disk.get("read", [])))]
            for read, write, t in zip(read_mb_s, write_mb_s, disk_time_points):
                entry_data = {
                    "name": entry_name,
                    "ts": t,
                    "read": read,
                    "write": write
                }
                data.append(entry_data)
        elif secondary_key == "cpu":
            cpu_usage = main_field.cpu
            cpu_time_points = [i * interval for i in range(len(cpu_usage))]
            for usage, t in zip(cpu_usage, cpu_time_points):
                entry_data = {
                    "name": entry_name,
                    "ts": t,
                    "usage": usage
                }
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
        fig = go.Figure()
        if self.key == "network":
            for col in ["send", "recv"]:
                fig.add_trace(
                    go.Scatter(
                        x=df["ts"],
                        y=df[col],
                        mode="lines",
                        name=f"{col.capitalize()} (MB/s)",
                        legendgroup=col,
                        line=dict(shape="linear"),
                        hoverinfo="x+y+name",
                    )
                )
            fig.update_traces(marker=dict(size=4))
            fig.update_layout(legend_title_text="Type")
        elif self.key == "disk":
            for col in ["read", "write"]:
                fig.add_trace(
                    go.Scatter(
                        x=df["ts"],
                        y=df[col],
                        mode="lines",
                        name=f"{col.capitalize()} (MB/s)",
                        legendgroup=col,
                        line=dict(shape="linear"),
                        hoverinfo="x+y+name",
                    )
                )
            fig.update_traces(marker=dict(size=4))
            fig.update_layout(legend_title_text="Type")
        elif self.key == "cpu":
            fig.add_trace(
                go.Scatter(
                    x=df["ts"],
                    y=df["usage"],
                    mode="lines",
                    name="CPU Usage (%)",
                    line=dict(shape="linear"),
                    hoverinfo="x+y+name",
                )
            )

        y_titles = {
            "network": "Network usage (MB/s)",
            "disk": "Disk I/O (MB/s)",
            "cpu": "CPU usage (%)"
        }
        fig.update_yaxes(title=y_titles.get(self.key, "Usage"))

        fig.update_layout(title=self.name, title_x=0.5,)

        return fig, ""
