import types
import pandas as pd
import plotly.graph_objects as go
import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common


BYTES_TO_MEGABYTES = 1024 * 1024

METRIC_TYPES = {
    "cpu": {
        "name": "CPU Usage",
        "y_title": "CPU usage (%)",
        "unit": "%"
    },
    "network": {
        "name": "Network Usage",
        "y_title": "Network usage (MB/s)",
        "unit": "MB/s"
    },
    "disk": {
        "name": "Disk Usage",
        "y_title": "Disk I/O (MB/s)",
        "unit": "MB/s"
    },
    "memory": {
        "name": "Memory Usage",
        "y_title": "Memory usage (%)",
        "unit": "%"
    }
}

COLOR_GREEN = "rgba(44,160,44,1)"
COLOR_GREEN_FILL = "rgba(44,160,44,0.14)"
COLOR_RED = "rgba(214,39,40,1)"
COLOR_RED_FILL = "rgba(214,39,40,0.14)"
COLOR_BLUE = "rgba(31,119,180,1)"
COLOR_JITTER_FILL_DEFAULT = "rgba(100,100,200,0.12)"
DEFAULT_LINE_COLOR = "rgba(50,50,50,1)"
JITTER_LINE_TRANSPARENT = "rgba(255,255,255,0)"


def register():
    for metric_type in METRIC_TYPES.keys():
        MetricUsage(metric_type)


def _to_mb_s(item, interval):
    if isinstance(item, types.SimpleNamespace):
        percentile_50th = (item.percentile_50th / BYTES_TO_MEGABYTES) / interval
        percentile_75th = (item.percentile_75th / BYTES_TO_MEGABYTES) / interval
        percentile_25th = (item.percentile_25th / BYTES_TO_MEGABYTES) / interval
        return types.SimpleNamespace(
            percentile_50th=percentile_50th,
            percentile_75th=percentile_75th,
            percentile_25th=percentile_25th
        )
    val = (item / BYTES_TO_MEGABYTES) / interval
    return types.SimpleNamespace(percentile_50th=val, percentile_75th=val, percentile_25th=val)


def _process_network_data(main_field, entry_name, interval):
    data = []
    if not hasattr(main_field, "network") or not main_field.network:
        return data

    send_data = main_field.network.get("send", [])
    recv_data = main_field.network.get("recv", [])

    if not send_data or not recv_data:
        return data

    mb_s_sent = [_to_mb_s(item, interval) for item in send_data]
    mb_s_recv = [_to_mb_s(item, interval) for item in recv_data]
    time_points = [i * interval for i in range(len(send_data))]

    for send, recv, timestamp in zip(mb_s_sent, mb_s_recv, time_points):
        data.append({
            "name": entry_name,
            "ts": timestamp,
            "send": send,
            "recv": recv
        })
    return data


def _process_disk_data(main_field, entry_name, interval):
    data = []
    if not hasattr(main_field, "disk") or not main_field.disk:
        return data

    read_data = main_field.disk.get("read", [])
    write_data = main_field.disk.get("write", [])

    if not read_data or not write_data:
        return data

    read_mb_s = [_to_mb_s(item, interval) for item in read_data]
    write_mb_s = [_to_mb_s(item, interval) for item in write_data]
    time_points = [i * interval for i in range(len(read_data))]

    for read, write, timestamp in zip(read_mb_s, write_mb_s, time_points):
        data.append({
            "name": entry_name,
            "ts": timestamp,
            "read": read,
            "write": write
        })
    return data


def _process_single_metric_data(main_field, entry_name, interval, metric_key):
    data = []
    if not hasattr(main_field, metric_key):
        return data

    metric_data = getattr(main_field, metric_key)
    if not metric_data:
        return data

    time_points = [i * interval for i in range(len(metric_data))]

    for usage, timestamp in zip(metric_data, time_points):
        data.append({
            "name": entry_name,
            "ts": timestamp,
            "usage": usage
        })
    return data


def generate_usage_data(entries, variables, main_key, secondary_key):
    data = []
    variables_copy = dict(variables)  # make a copy before modifying

    for entry in entries:
        main_field = entry.results.__dict__.get(main_key)
        if not main_field:
            continue

        entry_name = entry.get_name(variables_copy)
        interval = main_field.interval

        if secondary_key == "network":
            data.extend(_process_network_data(main_field, entry_name, interval))
        elif secondary_key == "disk":
            data.extend(_process_disk_data(main_field, entry_name, interval))
        elif secondary_key in ["cpu", "power", "memory"]:
            data.extend(_process_single_metric_data(main_field, entry_name, interval, secondary_key))

    return data


class MetricUsage:

    def __init__(self, metric_type):
        if metric_type not in METRIC_TYPES:
            supported_types = list(METRIC_TYPES.keys())
            error_msg = f"Unknown metric type: {metric_type}. Supported types: {supported_types}"
            raise ValueError(error_msg)

        self.key = metric_type
        self.metric_config = METRIC_TYPES[metric_type]
        self.name = f"System {self.metric_config['name']}"
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def _create_dual_metric_traces(self, df, metric_keys):
        traces_by_key = {}
        fill_colors = {
            "send": COLOR_GREEN_FILL,
            "recv": COLOR_RED_FILL,
            "read": COLOR_GREEN_FILL,
            "write": COLOR_RED_FILL,
        }
        line_colors = {
            "send": COLOR_GREEN,
            "recv": COLOR_RED,
            "read": COLOR_GREEN,
            "write": COLOR_RED,
        }
        for key in metric_keys:
            traces_for_key = []
            if df[key].apply(lambda v: isinstance(v, types.SimpleNamespace)).all():
                values = df[key].apply(lambda v: v.percentile_50th if isinstance(v, types.SimpleNamespace) else v)
                upper = df[key].apply(lambda v: v.percentile_75th if isinstance(v, types.SimpleNamespace) else 0)
                lower = df[key].apply(lambda v: v.percentile_25th if isinstance(v, types.SimpleNamespace) else 0)
                traces_for_key.append(
                    go.Scatter(
                        x=list(df["ts"]) + list(df["ts"][::-1]),
                        y=list(upper) + list(lower[::-1]),
                        fill="toself",
                        fillcolor=fill_colors.get(key, COLOR_JITTER_FILL_DEFAULT),
                        line=dict(color=JITTER_LINE_TRANSPARENT),
                        hoverinfo="skip",
                        name=f"Range (P25 - P75) ({key.capitalize()})",
                        showlegend=True,
                        legendgroup=key,
                    )
                )
                traces_for_key.append(
                    go.Scatter(
                        x=df["ts"],
                        y=values,
                        mode="lines",
                        name=f"{key.capitalize()} ({self.metric_config['unit']}) (Median)",
                        legendgroup=key,
                        line=dict(color=line_colors.get(key, DEFAULT_LINE_COLOR), width=2, shape="linear"),
                        hoverinfo="x+y+name",
                    )
                )
            else:
                traces_for_key.append(
                    go.Scatter(
                        x=df["ts"],
                        y=df[key],
                        mode="lines",
                        name=f"{key.capitalize()} ({self.metric_config['unit']})",
                        legendgroup=key,
                        line=dict(color=line_colors.get(key, DEFAULT_LINE_COLOR), width=2, shape="linear"),
                        hoverinfo="x+y+name",
                    )
                )
            traces_by_key[key] = traces_for_key
        return traces_by_key

    def _create_single_metric_trace(self, df):
        traces = []
        if df["usage"].apply(lambda v: isinstance(v, types.SimpleNamespace)).all():
            values = df["usage"].apply(lambda v: v.percentile_50th if isinstance(v, types.SimpleNamespace) else v)
            upper = df["usage"].apply(lambda v: v.percentile_75th if isinstance(v, types.SimpleNamespace) else 0)
            lower = df["usage"].apply(lambda v: v.percentile_25th if isinstance(v, types.SimpleNamespace) else 0)
            traces.append(
                go.Scatter(
                    x=list(df["ts"]) + list(df["ts"][::-1]),
                    y=list(upper) + list(lower[::-1]),
                    fill="toself",
                    fillcolor=COLOR_JITTER_FILL_DEFAULT,
                    line=dict(color=JITTER_LINE_TRANSPARENT),
                    hoverinfo="skip",
                    showlegend=True,
                    name="Range (P25 - P75)",
                )
            )
            traces.append(
                go.Scatter(
                    x=df["ts"],
                    y=values,
                    mode="lines",
                    name=f"{self.metric_config['name']} ({self.metric_config['unit']}) (Median)",
                    line=dict(color=COLOR_BLUE, width=2, shape="linear"),
                    hoverinfo="x+y+name",
                )
            )
            return traces
        else:
            return [
                go.Scatter(
                    x=df["ts"],
                    y=df["usage"],
                    mode="lines",
                    name=f"{self.metric_config['name']} ({self.metric_config['unit']})",
                    line=dict(shape="linear"),
                    hoverinfo="x+y+name",
                )
            ]

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        current_settings = cfg.get("current_settings", False)
        entries = common.Matrix.filter_records(current_settings)
        df = pd.DataFrame(generate_usage_data(entries, variables, "metrics", self.key))

        if df.empty:
            return None, "No data available..."

        df = df.sort_values(by=["ts", "name"], ascending=False)
        fig = go.Figure()

        if self.key in ["network", "disk"]:
            metric_keys = ["send", "recv"] if self.key == "network" else ["read", "write"]
            for _, group in df.groupby("name"):
                group = group.sort_values(by=["ts"])  # ensure increasing time
                traces_by_key = self._create_dual_metric_traces(group, metric_keys)
                for key in metric_keys:
                    for trace in traces_by_key.get(key, []):
                        fig.add_trace(trace)
            fig.update_traces(marker=dict(size=4))
            fig.update_layout(legend_title_text="Type")
        else:  # cpu or power or memory
            for _, group in df.groupby("name"):
                group = group.sort_values(by=["ts"])
                traces = self._create_single_metric_trace(group)
                for trace in traces:
                    fig.add_trace(trace)

        fig.update_yaxes(title=self.metric_config["y_title"])
        fig.update_xaxes(title="Time (s)")
        fig.update_layout(title=self.name, title_x=0.5)
        return fig, ""
