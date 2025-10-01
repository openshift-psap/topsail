import pandas as pd
import plotly.graph_objects as go
import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

# Constants
BYTES_TO_MB = 1024 * 1024

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


def register():
    """Register all metric usage visualizations."""
    for metric_type in METRIC_TYPES.keys():
        MetricUsage(metric_type)


def _process_network_data(main_field, entry_name, interval):
    """Process network usage data and return formatted entries."""
    data = []
    if not hasattr(main_field, "network") or not main_field.network:
        return data

    send_data = main_field.network.get("send", [])
    recv_data = main_field.network.get("recv", [])

    if not send_data or not recv_data:
        return data

    mb_s_sent = [(item / BYTES_TO_MB) / interval for item in send_data]
    mb_s_recv = [(item / BYTES_TO_MB) / interval for item in recv_data]
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
    """Process disk usage data and return formatted entries."""
    data = []
    if not hasattr(main_field, "disk") or not main_field.disk:
        return data

    read_data = main_field.disk.get("read", [])
    write_data = main_field.disk.get("write", [])

    if not read_data or not write_data:
        return data

    read_mb_s = [(item / BYTES_TO_MB) / interval for item in read_data]
    write_mb_s = [(item / BYTES_TO_MB) / interval for item in write_data]
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
    """Process single metric data (CPU or Power) and return formatted entries."""
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
    """Generate usage data for visualization from entries."""
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
    """Visualization class for system metric usage (CPU, Network, Disk, Power)."""

    def __init__(self, metric_type):
        """Initialize with a specific metric type."""
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
        """Handle hover events on the plot."""
        return "nothing"

    def _create_dual_metric_traces(self, df, metric_keys):
        """Create traces for metrics with dual values (network, disk)."""
        traces = []
        for key in metric_keys:
            traces.append(
                go.Scatter(
                    x=df["ts"],
                    y=df[key],
                    mode="lines",
                    name=f"{key.capitalize()} ({self.metric_config['unit']})",
                    legendgroup=key,
                    line=dict(shape="linear"),
                    hoverinfo="x+y+name",
                )
            )
        return traces

    def _create_single_metric_trace(self, df):
        """Create trace for single-value metrics (CPU, power, memory)."""
        return go.Scatter(
            x=df["ts"],
            y=df["usage"],
            mode="lines",
            name=f"{self.metric_config['name']} ({self.metric_config['unit']})",
            line=dict(shape="linear"),
            hoverinfo="x+y+name",
        )

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        """Generate the plot for the metric usage."""
        current_settings = cfg.get("current_settings", False)
        entries = common.Matrix.filter_records(current_settings)
        df = pd.DataFrame(generate_usage_data(entries, variables, "metrics", self.key))

        if df.empty:
            return None, "No data available..."

        df = df.sort_values(by=["ts", "name"], ascending=False)
        fig = go.Figure()

        # Create traces based on metric type
        if self.key in ["network", "disk"]:
            metric_keys = ["send", "recv"] if self.key == "network" else ["read", "write"]
            traces = self._create_dual_metric_traces(df, metric_keys)
            for trace in traces:
                fig.add_trace(trace)
            fig.update_traces(marker=dict(size=4))
            fig.update_layout(legend_title_text="Type")
        else:  # cpu or power or memory
            fig.add_trace(self._create_single_metric_trace(df))

        # Set y-axis title and overall layout
        fig.update_yaxes(title=self.metric_config["y_title"])
        fig.update_xaxes(title="Time (s)")
        fig.update_layout(title=self.name, title_x=0.5)

        return fig, ""
