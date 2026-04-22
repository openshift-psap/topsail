import plotly.graph_objects as go
import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common
import projects.matrix_benchmarking.visualizations.helpers.plotting.units as units
from .utils.config import generate_display_config_label


COLOR_GREEN = "rgba(44,160,44,1)"
COLOR_GREEN_FILL = "rgba(44,160,44,0.14)"
COLOR_RED = "rgba(214,39,40,1)"
COLOR_RED_FILL = "rgba(214,39,40,0.14)"
COLOR_BLUE = "rgba(31,119,180,1)"
DEFAULT_LINE_COLOR = "rgba(50,50,50,1)"

COLOR_PALETTE = [
    COLOR_BLUE,                    # blue
    COLOR_RED,                     # red
    COLOR_GREEN,                   # green
    "rgba(255,127,14,1)",          # orange
    "rgba(148,103,189,1)",         # purple
    "rgba(140,86,75,1)",           # brown
    "rgba(227,119,194,1)",         # pink
    "rgba(127,127,127,1)",         # gray
]

SYNTHETIC_PLOT_NAME = "Comparison: Synthetic Benchmark"
PERFORMANCE_PLOT_NAME = "Comparison: Performance Metrics"


def register():
    SyntheticBenchmarkComparisonPlot()
    PerformanceComparisonPlot()


def _get_fileio_sort_key(config):
    return (config.get("benchmark_read_throughput") or 0) + \
           (config.get("benchmark_write_throughput") or 0)


def _get_standard_sort_key(config):
    return config.get("benchmark_value") or 0


def _create_synthetic_bench_plot(configurations):
    if not configurations:
        return None

    if configurations[0].get("metric_type") != "synthetic_benchmark":
        return None

    benchmark_type = configurations[0].get("benchmark_type", "")
    is_fileio = 'fileio' in benchmark_type

    if is_fileio:
        sorted_configurations = sorted(configurations, key=_get_fileio_sort_key, reverse=True)

        read_bars = []
        write_bars = []
        for idx, config in enumerate(sorted_configurations):
            config_label = generate_display_config_label(config, configurations)
            read_value = config.get("benchmark_read_throughput") or 0
            write_value = config.get("benchmark_write_throughput") or 0

            read_bars.append(
                go.Bar(
                    x=[config_label],
                    y=[read_value],
                    name="Read (MiB/s)",
                    marker_color=COLOR_GREEN,
                    marker_line_color=DEFAULT_LINE_COLOR,
                    marker_line_width=1,
                    width=0.25,
                    text=[f'{read_value:.2f} MiB/s'],
                    textposition='outside',
                    textfont=dict(size=14),
                    hovertemplate=f'<b>{config_label}</b><br>Read: %{{y:.2f}} MiB/s<extra></extra>',
                    cliponaxis=False,
                    showlegend=(idx == 0),
                    legendgroup='read'
                )
            )
            write_bars.append(
                go.Bar(
                    x=[config_label],
                    y=[write_value],
                    name="Write (MiB/s)",
                    marker_color=COLOR_RED,
                    marker_line_color=DEFAULT_LINE_COLOR,
                    marker_line_width=1,
                    width=0.25,
                    text=[f'{write_value:.2f} MiB/s'],
                    textposition='outside',
                    textfont=dict(size=14),
                    hovertemplate=f'<b>{config_label}</b><br>Write: %{{y:.2f}} MiB/s<extra></extra>',
                    cliponaxis=False,
                    showlegend=(idx == 0),
                    legendgroup='write'
                )
            )

        all_values = [
            v for config in sorted_configurations
            for v in [config.get("benchmark_read_throughput") or 0, config.get("benchmark_write_throughput") or 0]
        ]
        y_max = max(all_values) if all_values else 1
        y_axis_min = 0
        y_axis_max = y_max * 1.25

        fig = go.Figure(data=read_bars + write_bars)
        fig.update_layout(
            barmode='group',
            bargap=0.35,
            bargroupgap=0.08,
            title='File I/O Benchmark Comparison',
            title_font_size=16,
            title_x=0.5,
            xaxis_title='Configuration',
            xaxis_tickfont_size=12,
            yaxis_title='Throughput (MiB/s)',
            yaxis_tickfont_size=11,
            yaxis_range=[y_axis_min, y_axis_max],
            hovermode='closest',
            height=550,
            showlegend=True,
            legend_font_size=11,
            legend=dict(
                orientation='h',
                x=0.5, xanchor='center',
                y=-0.18, yanchor='top',
                bgcolor="rgba(255,255,255,0.8)"
            ),
            margin=dict(l=80, r=80, t=100, b=140),
            plot_bgcolor='rgba(240, 240, 245, 0.5)',
            paper_bgcolor='white',
            font=dict(family="Arial, sans-serif", size=11, color="#333")
        )
    else:
        sorted_configurations = sorted(configurations, key=_get_standard_sort_key, reverse=True)
        benchmark_title = configurations[0].get("benchmark_title", "Result")

        benchmark_unit = configurations[0].get("benchmark_unit", "")
        unit_suffix = f" {benchmark_unit}" if benchmark_unit else ""
        yaxis_label = f"{benchmark_title} ({benchmark_unit})" if benchmark_unit else benchmark_title

        bars = []
        for idx, config in enumerate(sorted_configurations):
            color = COLOR_PALETTE[idx % len(COLOR_PALETTE)]
            config_label = generate_display_config_label(config, configurations)
            value = config.get("benchmark_value") or 0

            bars.append(
                go.Bar(
                    x=[config_label],
                    y=[value],
                    name=config_label,
                    marker_color=color,
                    marker_line_color=DEFAULT_LINE_COLOR,
                    marker_line_width=1,
                    width=0.3,
                    text=[f'{value:.2f}{unit_suffix}'],
                    textposition='outside',
                    textfont=dict(size=14),
                    cliponaxis=False,
                    hovertemplate=f'<b>{config_label}</b><br>{benchmark_title}: %{{y:.2f}}{unit_suffix}<extra></extra>',
                    showlegend=False
                )
            )

        std_values = [config.get("benchmark_value") or 0 for config in sorted_configurations]
        y_max = max(std_values) if std_values else 1
        y_axis_min = 0
        y_axis_max = y_max * 1.25

        fig = go.Figure(data=bars)
        fig.update_layout(
            bargap=0.45,
            title=f'{benchmark_title} Benchmark Comparison',
            title_font_size=16,
            title_x=0.5,
            xaxis_title='Configuration',
            xaxis_tickfont_size=12,
            yaxis_title=yaxis_label,
            yaxis_tickfont_size=11,
            yaxis_range=[y_axis_min, y_axis_max],
            hovermode='closest',
            height=550,
            showlegend=False,
            margin=dict(l=80, r=80, t=100, b=120),
            plot_bgcolor='rgba(240, 240, 245, 0.5)',
            paper_bgcolor='white',
            font=dict(family="Arial, sans-serif", size=11, color="#333")
        )

    return fig


def _create_exec_time_plot(configurations):
    if not configurations:
        return None

    sorted_configurations = sorted(
        configurations,
        key=lambda c: c.get("execution_time_95th_percentile", 0) or 0
    )

    bars = []
    annotations = []
    for idx, config in enumerate(sorted_configurations):
        color = COLOR_PALETTE[idx % len(COLOR_PALETTE)]
        config_label = generate_display_config_label(config, configurations)
        exec_time = config.get("execution_time_95th_percentile") or 0

        bars.append(
            go.Bar(
                x=[config_label],
                y=[exec_time],
                name=config_label,
                marker_color=color,
                marker_opacity=0.85,
                marker_line_color=DEFAULT_LINE_COLOR,
                marker_line_width=1,
                width=0.3,
                hovertemplate=(
                    f'<b>{config_label}</b><br>'
                    f'Execution Time (P95): {units.format_duration(exec_time)}'
                    '<extra></extra>'
                ),
                showlegend=False
            )
        )

        annotations.append(dict(
            x=config_label,
            y=exec_time,
            text=f'{units.format_duration(exec_time)}',

            showarrow=False,
            yshift=10,
            font=dict(size=16, color=DEFAULT_LINE_COLOR),
            xanchor='center'
        ))

    fig = go.Figure(data=bars)

    valid_times = [c.get("execution_time_95th_percentile") or 0 for c in sorted_configurations]
    y_max = max(valid_times) if valid_times else 1
    y_axis_min = 0
    y_axis_max = y_max * 1.25  # headroom for annotation labels above bars

    fig.update_layout(
        title='Performance Metrics Comparison',
        title_font_size=16,
        title_x=0.5,
        xaxis_title='Configuration',
        xaxis_tickfont_size=12,
        xaxis_tickangle=-10,
        yaxis_title='Execution Time (seconds)',
        yaxis_tickfont_size=11,
        yaxis_range=[y_axis_min, y_axis_max],
        hovermode='closest',
        height=500,
        showlegend=False,
        annotations=annotations,
        margin=dict(l=80, r=80, t=80, b=120),
        plot_bgcolor='rgba(240, 240, 245, 0.5)',
        paper_bgcolor='white',
        font=dict(family="Arial, sans-serif", size=11, color="#333"),
        bargap=0.5,
    )

    return fig


class SyntheticBenchmarkComparisonPlot:
    """
    Registered plot stat for synthetic benchmark comparisons.
    Mirrors the MetricUsage class pattern from metrics.py.
    """

    def __init__(self):
        self.name = SYNTHETIC_PLOT_NAME
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        configurations = cfg.get("configurations", [])
        fig = _create_synthetic_bench_plot(configurations)
        if fig is None:
            return None, "No synthetic benchmark data available"
        return fig, ""


class PerformanceComparisonPlot:
    """
    Registered plot stat for performance metrics comparisons.
    Mirrors the MetricUsage class pattern from metrics.py.
    """

    def __init__(self):
        self.name = PERFORMANCE_PLOT_NAME
        self.id_name = self.name

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_hover(self, meta_value, variables, figure, data, click_info):
        return "nothing"

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        configurations = cfg.get("configurations", [])
        fig = _create_exec_time_plot(configurations)
        if fig is None:
            return None, "No performance data available"
        return fig, ""
