from dash import html, dcc
import json
import itertools
import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common
import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report
import projects.matrix_benchmarking.visualizations.helpers.plotting.styles_css as css
import projects.matrix_benchmarking.visualizations.helpers.plotting.html as html_elements
import projects.matrix_benchmarking.visualizations.helpers.plotting.units as units

from .report import getInfo

BYTES_TO_MB = 1024 * 1024
METRIC_TYPES = ['cpu', 'memory', 'power', 'network_send', 'network_recv', 'disk_read', 'disk_write']
METRIC_LABELS = {
    'cpu': ('Average CPU Usage', '%'),
    'memory': ('Average Memory Usage', '%'),
    'power': ('Average Power Usage', 'W'),
    'network_send': ('Average Network Send', 'MB/s'),
    'network_recv': ('Average Network Recv', 'MB/s'),
    'disk_read': ('Average Disk Read', 'MB/s'),
    'disk_write': ('Average Disk Write', 'MB/s')
}


def calculate_single_metric_average(metrics, metric_type, interval=1):
    if metric_type == 'cpu':
        if hasattr(metrics, 'cpu') and metrics.cpu:
            return sum(metrics.cpu) / len(metrics.cpu)
    elif metric_type == 'memory':
        if hasattr(metrics, 'memory') and metrics.memory:
            return sum(metrics.memory) / len(metrics.memory)
    elif metric_type == 'power':
        if hasattr(metrics, 'power') and metrics.power:
            return sum(metrics.power) / len(metrics.power)
    elif metric_type == 'network_send':
        if hasattr(metrics, 'network') and metrics.network:
            send_data = metrics.network.get("send", [])
            if send_data:
                send_mb_s = [(item / BYTES_TO_MB) / interval for item in send_data]
                return sum(send_mb_s) / len(send_mb_s)
    elif metric_type == 'network_recv':
        if hasattr(metrics, 'network') and metrics.network:
            recv_data = metrics.network.get("recv", [])
            if recv_data:
                recv_mb_s = [(item / BYTES_TO_MB) / interval for item in recv_data]
                return sum(recv_mb_s) / len(recv_mb_s)
    elif metric_type == 'disk_read':
        if hasattr(metrics, 'disk') and metrics.disk:
            read_data = metrics.disk.get("read", [])
            if read_data:
                read_mb_s = [(item / BYTES_TO_MB) / interval for item in read_data]
                return sum(read_mb_s) / len(read_mb_s)
    elif metric_type == 'disk_write':
        if hasattr(metrics, 'disk') and metrics.disk:
            write_data = metrics.disk.get("write", [])
            if write_data:
                write_mb_s = [(item / BYTES_TO_MB) / interval for item in write_data]
                return sum(write_mb_s) / len(write_mb_s)
    return None


def calculate_config_metrics(settings):
    entries = common.Matrix.filter_records(settings)
    if not entries:
        return {}

    config_averages = {}

    for entry in entries:
        metrics = entry.results.__dict__.get("metrics")
        if not metrics:
            continue

        interval = getattr(metrics, 'interval', 1)

        for metric_type in METRIC_TYPES:
            avg_value = calculate_single_metric_average(metrics, metric_type, interval)
            if avg_value is not None:
                config_averages[metric_type] = avg_value

    return config_averages


def create_metric_value_cell(value, unit, is_min=False, is_max=False, is_single=False):
    if value is None:
        return html.Td("N/A", style=css.STYLE_TABLE_CELL)

    if is_min and not is_single:
        return html.Td([
            html.Span(f"{value:.2f} {unit}", style={'font-weight': 'bold'}),
            html.Br(),
            html.Small("🔽 LOWEST", style={'color': '#28a745', 'font-weight': 'bold'})
        ], style=css.STYLE_TABLE_CELL_HIGHLIGHT)
    elif is_max and not is_single:
        return html.Td([
            html.Span(f"{value:.2f} {unit}"),
            html.Br(),
            html.Small("🔼 HIGHEST", style={'color': '#dc3545', 'font-weight': 'bold'})
        ], style=css.STYLE_TABLE_CELL)
    else:
        return html.Td(f"{value:.2f} {unit}", style=css.STYLE_TABLE_CELL)


def register():
    BenchmarkComparisonReport()


class BenchmarkComparisonReport():
    def __init__(self):
        self.name = "report: Benchmark Comparison Report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        """Generate a side-by-side comparison report for multiple configurations, grouped by benchmark."""
        ordered_vars, settings, setting_lists, variables, cfg = args

        report_components = [
            dcc.Markdown(f'<style>{css.EMBEDDED_CSS}{css.COMPARISON_CSS}</style>', dangerously_allow_html=True),
            html.H1("Container Engine Benchmark Comparison", style=css.STYLE_H1)
        ]

        configurations_by_benchmark = getAllConfigurationInfo(ordered_vars, setting_lists, variables)

        if configurations_by_benchmark:
            generate_comparison_report(report_components, configurations_by_benchmark, args)
        else:
            report_components.append(
                html.Div("No configuration data found for comparison", style=css.STYLE_ERROR_MESSAGE)
            )

        return None, html.Div(report_components, style=css.STYLE_CONTAINER, className='report-container')


def generate_config_label(settings, exclude_benchmark=False):
    label_parts = []

    if "container_engine" in settings:
        label_parts.append(f"{settings['container_engine']}")
    if "benchmark" in settings and not exclude_benchmark:
        benchmark_name = settings['benchmark'].replace('_', ' ').title()
        label_parts.append(f"{benchmark_name}")
    if "benchmark_runs" in settings and settings["benchmark_runs"] != 1:
        label_parts.append(f"{settings['benchmark_runs']} runs")

    for key, value in settings.items():
        if key not in ["container_engine", "benchmark", "benchmark_runs", "stats"] and len(label_parts) < 4:
            label_parts.append(f"{key}: {value}")

    return " | ".join(label_parts) if label_parts else "Configuration"


def getAllConfigurationInfo(ordered_vars, setting_lists, variables):
    configurations_by_benchmark = {}

    for settings_values in sorted(itertools.product(*setting_lists), key=lambda x: x[0][0] if x else None):
        current_settings = dict(settings_values)
        if "stats" in current_settings:
            del current_settings["stats"]

        info = getInfo(current_settings)
        if info:
            benchmark = current_settings.get("benchmark", "unknown")
            info["config_label"] = generate_config_label(current_settings, exclude_benchmark=True)
            info["settings"] = current_settings

            if benchmark not in configurations_by_benchmark:
                configurations_by_benchmark[benchmark] = []
            configurations_by_benchmark[benchmark].append(info)

    return configurations_by_benchmark


def _analyze_field_differences(configurations, field_map, info_getter, field_processor=None):
    shared = {}
    different = {}

    for field_key, field_display in field_map.items():
        values = []
        for config in configurations:
            info = info_getter(config)
            value = info.get(field_key, "N/A")

            if field_processor:
                value = field_processor(field_key, value)

            values.append(value)

        unique_values = list(set(values))
        if len(unique_values) == 1:
            shared[field_key] = unique_values[0]
        else:
            different[field_key] = True

    return shared, different


def find_shared_and_different_info(configurations):
    if len(configurations) <= 1:
        return {}, {}

    shared_info = {}
    different_info = {}

    system_fields = ["Model_id", "CPU_model", "CPU_cores", "Memory", "OS_version", "Kernel_version"]
    system_field_map = {field: field for field in system_fields}

    def get_system_info(config):
        return config.get("system", {})

    shared_system, different_system = _analyze_field_differences(
        configurations, system_field_map, get_system_info
    )
    shared_info["system"] = shared_system
    different_info["system"] = different_system

    engine_fields = [
        "Container_engine_platform", "Client_version", "Host_version",
        "Mode", "Host_cpu", "Host_memory", "Host_kernel"
    ]
    engine_field_map = {field: field for field in engine_fields}

    def get_engine_info(config):
        return config.get("container_engine_info", {})

    shared_engine, different_engine = _analyze_field_differences(
        configurations, engine_field_map, get_engine_info, _process_engine_field_value
    )
    shared_info["engine"] = shared_engine
    different_info["engine"] = different_engine

    common_fields = ["runs", "container_engine_provider", "command", "timestamp"]
    for field in common_fields:
        values = [config.get(field, "N/A") for config in configurations]
        unique_values = list(set(values))
        if len(unique_values) == 1:
            shared_info[field] = unique_values[0]
        else:
            different_info[field] = True

    return shared_info, different_info


def _create_summary_info_card(shared_info):
    summary_items = []

    if shared_info.get("command") and shared_info["command"] != "N/A":
        summary_items.append(("Command", html.Code(shared_info["command"]), False, False))

    if shared_info.get("timestamp") and shared_info["timestamp"] != "N/A":
        summary_items.append(("Timestamp", shared_info["timestamp"], False, False))

    if summary_items:
        summary_items[-1] = (summary_items[-1][0], summary_items[-1][1], True, summary_items[-1][3])
        return html_elements.info_card("Benchmark Summary", summary_items)

    return None


def _create_host_info_card(shared_info):
    host_items = []
    system_field_map = {
        "Model_id": "Model ID",
        "CPU_model": "CPU",
        "CPU_cores": "Cores",
        "Memory": "Memory",
        "OS_version": "OS Version",
        "Kernel_version": "Kernel"
    }

    if shared_info.get("system"):
        for field_key, field_display in system_field_map.items():
            value = shared_info["system"].get(field_key)
            if value and value != "N/A":
                host_items.append((field_display, value, False, False))

    if host_items:
        host_items[-1] = (host_items[-1][0], host_items[-1][1], True, host_items[-1][3])
        return html_elements.info_card("Host System Information", host_items)

    return None


def _create_engine_info_card(shared_info):
    engine_items = []
    engine_field_map = {
        "Container_engine_platform": "Engine",
        "Client_version": "Client Version",
        "Host_version": "Host Version",
        "Mode": "Rootless Mode",
        "Host_cpu": "Host CPU",
        "Host_memory": "Host Memory",
        "Host_kernel": "Host Kernel",
    }

    if shared_info.get("engine"):
        for field_key, field_display in engine_field_map.items():
            value = shared_info["engine"].get(field_key)
            if value is not None and value != "N/A":
                engine_items.append((field_display, value, False, False))

    if shared_info.get("container_engine_provider") and shared_info["container_engine_provider"] != "N/A":
        engine_items.append(("Provider", shared_info["container_engine_provider"], False, False))

    if engine_items:
        engine_items[-1] = (engine_items[-1][0], engine_items[-1][1], True, engine_items[-1][3])
        return html_elements.info_card("Container Engine Information", engine_items)

    return None


def create_shared_info_section(shared_info, configurations):
    cards = []

    summary_card = _create_summary_info_card(shared_info)
    if summary_card:
        cards.append(summary_card)

    host_card = _create_host_info_card(shared_info)
    if host_card:
        cards.append(host_card)

    engine_card = _create_engine_info_card(shared_info)
    if engine_card:
        cards.append(engine_card)

    if cards:
        return html.Div(cards, style=css.STYLE_INFO_ROW)
    else:
        return html.Div("No shared configuration information found")


def calculate_usage_deltas(configurations):
    if len(configurations) < 2:
        return {}

    usage_averages = {}

    for config in configurations:
        config_label = config.get("config_label", "Unknown")
        settings = config.get("settings", {})
        config_averages = calculate_config_metrics(settings)
        usage_averages[config_label] = config_averages

    deltas = {}

    for metric in METRIC_TYPES:
        metric_values = []
        metric_labels = []

        for config_label, averages in usage_averages.items():
            if metric in averages:
                metric_values.append(averages[metric])
                metric_labels.append(config_label)

        if len(metric_values) >= 2:
            min_val = min(metric_values)
            max_val = max(metric_values)
            delta = max_val - min_val

            min_idx = metric_values.index(min_val)
            max_idx = metric_values.index(max_val)

            deltas[metric] = {
                'delta': delta,
                'min_value': min_val,
                'max_value': max_val,
                'min_config': metric_labels[min_idx],
                'max_config': metric_labels[max_idx],
                'percentage': (delta / min_val * 100) if min_val > 0 else 0
            }

    return deltas


def _create_comparison_table_header(configurations):
    header_cells = [html.Th("", style=css.STYLE_TABLE_HEADER)]
    for config in configurations:
        header_cells.append(html.Th(config["config_label"], style=css.STYLE_TABLE_HEADER))

    if len(configurations) > 1:
        header_cells.append(html.Th("Performance Delta", style=css.STYLE_TABLE_HEADER))

    return html.Tr(header_cells)


def _create_execution_time_row(configurations):
    exec_times = []
    exec_time_cells = [html.Td("Execution Time", style=css.STYLE_TABLE_CELL)]

    for config in configurations:
        exec_time = config.get("exec_time", 0)
        exec_times.append(exec_time)
        runs = config.get("runs", 1)
        formatted_content = "N/A"
        if exec_time:
            formatted_content = [
                html.Span(
                    f"{units.format_duration(exec_time)}",
                    style=css.STYLE_INFO_VALUE_HIGHLIGHT
                ),
                html.Br(),
                html.Small(
                    f"(Average of {runs} runs)",
                    style=css.STYLE_SMALL_TEXT
                )
            ]

        exec_time_cells.append(html.Td(formatted_content, style=css.STYLE_TABLE_CELL))

    if len(configurations) > 1 and all(t > 0 for t in exec_times):
        min_time = min(exec_times)
        max_time = max(exec_times)
        delta = max_time - min_time
        delta_percentage = ((max_time - min_time) / min_time) * 100 if min_time > 0 else 0

        fastest_idx = exec_times.index(min_time)

        for i, config in enumerate(configurations):
            if i == fastest_idx:
                runs = config.get("runs", 1)
                exec_time_cells[i + 1] = html.Td([
                    html.Span(units.format_duration(exec_times[i]), style={
                        'font-weight': 'bold', **css.STYLE_INFO_VALUE_HIGHLIGHT
                    }),
                    html.Br(),
                    html.Small(f"(Average of {runs} runs)", style=css.STYLE_SMALL_TEXT),
                    html.Br(),
                    html.Small("⚡ FASTEST", style={'color': '#28a745', 'font-weight': 'bold'})
                ], style=css.STYLE_TABLE_CELL_HIGHLIGHT)

        delta_info = html.Td([
            html.Span(f"Δ {units.format_duration(delta)}", style={'font-weight': 'bold'}),
            html.Br(),
            html.Small(f"({delta_percentage:.1f}% faster)", style={'color': '#6c757d'})
        ], style=css.STYLE_TABLE_CELL)
        exec_time_cells.append(delta_info)

    return html.Tr(exec_time_cells)


def _create_info_row(label, configurations, field_name, has_delta=True):
    cells = [html.Td(label, style=css.STYLE_TABLE_CELL)]

    for config in configurations:
        value = config.get(field_name, "N/A")
        if field_name == "command" and value != "N/A":
            cells.append(html.Td(html.Code(value), style=css.STYLE_TABLE_CELL))
        else:
            cells.append(html.Td(value, style=css.STYLE_TABLE_CELL))

    if has_delta and len(configurations) > 1:
        cells.append(html.Td("-", style=css.STYLE_TABLE_CELL))

    return html.Tr(cells)


def _create_metrics_rows(configurations):
    """Create metric rows for performance comparison table."""
    rows = []

    if not any(config.get('exec_time', 0) > 5 for config in configurations):
        return rows

    separator_cells = [html.Td("", style=css.STYLE_TABLE_CELL) for _ in range(len(configurations) + 2)]
    rows.append(html.Tr(separator_cells))

    config_metrics = {}
    for config in configurations:
        config_label = config.get("config_label", "Unknown")
        settings = config.get("settings", {})
        config_metrics[config_label] = calculate_config_metrics(settings)

    for metric_type, (label, unit) in METRIC_LABELS.items():
        metric_values = []
        config_labels = []

        for config_label, metrics in config_metrics.items():
            if metric_type in metrics:
                metric_values.append(metrics[metric_type])
                config_labels.append(config_label)

        if len(metric_values) >= 1:
            metric_cells = [html.Td(label, style=css.STYLE_TABLE_CELL)]

            min_val = min(metric_values) if metric_values else 0
            max_val = max(metric_values) if metric_values else 0
            is_single = len(metric_values) == 1

            for config in configurations:
                config_label = config.get("config_label", "Unknown")
                config_value = config_metrics[config_label].get(metric_type)

                is_min = config_value == min_val and not is_single
                is_max = config_value == max_val and not is_single

                value_cell = create_metric_value_cell(config_value, unit, is_min, is_max, is_single)
                metric_cells.append(value_cell)

            if len(configurations) > 1 and len(metric_values) >= 2:
                delta = max_val - min_val
                delta_percentage = (delta / min_val * 100) if min_val > 0 else 0
                delta_display = html.Td([
                    html.Span(f"Δ {delta:.2f} {unit}", style={'font-weight': 'bold'}),
                    html.Br(),
                    html.Small(f"({delta_percentage:.1f}% difference)", style={'color': '#6c757d'})
                ], style=css.STYLE_TABLE_CELL)
                metric_cells.append(delta_display)
            elif len(configurations) > 1:
                metric_cells.append(html.Td("-", style=css.STYLE_TABLE_CELL))

            rows.append(html.Tr(metric_cells))

    return rows


def create_performance_comparison_table(configurations):
    if not configurations:
        return None

    rows = [_create_comparison_table_header(configurations)]

    rows.append(_create_execution_time_row(configurations))

    rows.append(_create_info_row("Command", configurations, "command"))
    rows.append(_create_info_row("Timestamp", configurations, "timestamp"))

    rows.extend(_create_metrics_rows(configurations))

    return html.Table(rows, style=css.STYLE_COMPARISON_TABLE)


def _create_table_header(configurations, first_column_title="", delta_column=True):
    header_cells = [html.Th(first_column_title, style=css.STYLE_TABLE_HEADER)]
    for config in configurations:
        header_cells.append(html.Th(config["config_label"], style=css.STYLE_TABLE_HEADER))

    if delta_column and len(configurations) > 1:
        header_cells.append(html.Th("Performance Delta", style=css.STYLE_TABLE_HEADER))

    return html.Tr(header_cells)


def _create_table_row_from_field_map(configurations, field_map, info_getter, field_processor=None):
    rows = []

    for field_key, field_display in field_map.items():
        row_cells = [html.Td(field_display, style=css.STYLE_TABLE_CELL)]
        values = []

        for config in configurations:
            info = info_getter(config)
            value = info.get(field_key, "N/A")

            if field_processor:
                value = field_processor(field_key, value)

            values.append(value)
            row_cells.append(html.Td(value, style=css.STYLE_TABLE_CELL))

        if len(set(str(v) for v in values)) > 1:
            rows.append(html.Tr(row_cells))

    return rows


def _process_engine_field_value(field_key, value):
    if field_key == "Host_memory" and value != "N/A":
        try:
            value = units.human_readable_size(int(value))
        except (TypeError, ValueError):
            pass
    return value


def create_system_differences_table(configurations, different_info):
    """Create table showing system property differences."""
    if not different_info.get("system"):
        return None

    system_field_map = {
        "Model_id": "Model ID",
        "CPU_model": "CPU Model",
        "CPU_cores": "CPU Cores",
        "Memory": "Memory",
        "OS_version": "OS Version",
        "Kernel_version": "Kernel Version"
    }

    header_row = _create_table_header(configurations, "System Property", delta_column=False)

    filtered_field_map = {
        k: v for k, v in system_field_map.items()
        if different_info["system"].get(k)
    }

    if not filtered_field_map:
        return None

    rows = [header_row]

    def get_system_info(config):
        return config.get("system", {})

    rows.extend(_create_table_row_from_field_map(configurations, filtered_field_map, get_system_info))

    return html.Table(rows, style=css.STYLE_COMPARISON_TABLE) if len(rows) > 1 else None


def create_engine_differences_table(configurations, different_info):
    header_row = _create_table_header(configurations, "Engine Property", delta_column=False)
    rows = [header_row]

    if different_info.get("container_engine_provider"):
        row_cells = [html.Td("Provider", style=css.STYLE_TABLE_CELL)]
        for config in configurations:
            provider = config.get("container_engine_provider", "N/A")
            row_cells.append(html.Td(provider, style=css.STYLE_TABLE_CELL))
        rows.append(html.Tr(row_cells))

    if different_info.get("container_engine"):
        row_cells = [html.Td("Engine", style=css.STYLE_TABLE_CELL)]
        for config in configurations:
            engine = config.get("settings", {}).get("container_engine", "N/A")
            row_cells.append(html.Td(engine, style=css.STYLE_TABLE_CELL))
        rows.append(html.Tr(row_cells))

    if different_info.get("engine"):
        engine_field_map = {
            "Container_engine_platform": "Engine",
            "Client_version": "Client Version",
            "Host_version": "Host Version",
            "Mode": "Rootless Mode",
            "Host_cpu": "Host CPU",
            "Host_memory": "Host Memory",
            "Host_kernel": "Host Kernel"
        }

        filtered_field_map = {
            k: v for k, v in engine_field_map.items()
            if different_info["engine"].get(k)
        }

        def get_engine_info(config):
            return config.get("container_engine_info", {})

        rows.extend(_create_table_row_from_field_map(
            configurations, filtered_field_map, get_engine_info, _process_engine_field_value
        ))

    return html.Table(rows, style=css.STYLE_COMPARISON_TABLE) if len(rows) > 1 else None


def create_differences_comparison_table(configurations, different_info):
    if not configurations or len(configurations) < 2:
        return html.Div("No differences found between configurations")

    tables = []

    perf_table = create_performance_comparison_table(configurations)
    if perf_table:
        tables.append(html.Div([
            html.H4("Performance Metrics", style=css.STYLE_H4),
            perf_table
        ]))

    if different_info.get("system"):
        system_table = create_system_differences_table(configurations, different_info)
        if system_table:
            tables.append(html.Div([
                html.H4("Host System Differences", style=css.STYLE_H4),
                system_table
            ]))

    if different_info.get("engine") or different_info.get("runs"):
        engine_table = create_engine_differences_table(configurations, different_info)
        if engine_table:
            tables.append(html.Div([
                html.H4("Container Engine Differences", style=css.STYLE_H4),
                engine_table
            ]))

    if tables:
        return html.Div([table for table in tables if table], style={'margin-bottom': '1rem'})
    else:
        return html.Div("No differences found between configurations")


def create_technical_details_section(configurations):
    if not configurations:
        return None

    details_sections = []
    for i, config in enumerate(configurations):
        config_label = config.get("config_label", f"Configuration {i+1}")
        container_engine_full = config.get("container_engine_full", {})

        details_sections.append(html.Div([
            html.H5(f"{config_label}", style=css.STYLE_H4),
            html.Pre(
                json.dumps(container_engine_full, indent=2),
                style=css.STYLE_JSON_PRE
            )
        ], style={'margin-bottom': '1rem'}))

    return html.Details([
        html.Summary('Click for Full Technical Details', style=css.STYLE_DETAILS_SUMMARY),
        html.Div(details_sections, style=css.STYLE_DETAILS_CONTENT)
    ], style=css.STYLE_DETAILS)


def create_plots_section(configurations, args):
    if not configurations:
        return None

    # Check if any configuration has execution time > 5 seconds
    has_long_benchmarks = any(config.get('exec_time', 0) > 5 for config in configurations)

    if not has_long_benchmarks:
        return None

    plot_names = [
        "System CPU Usage",
        "System Power Usage",
        "System Memory Usage",
        "System Network Usage",
        "System Disk Usage"
    ]

    plot_sections = []
    for config in configurations:
        if config.get('exec_time', 0) > 5:  # Only show plots for longer benchmarks
            config_label = config.get("config_label", "Configuration")
            settings = config.get("settings", {})

            plot_cards = [
                html_elements.plot_card(name, report.set_config(dict(current_settings=settings), args))
                for name in plot_names
            ]

            plot_sections.append(html.Div([
                html.H5(f"{config_label} - System Monitoring", style=css.STYLE_H4),
                html.Div(plot_cards, style=css.STYLE_PLOTS_GRID, className='plots-grid-responsive')
            ], style={'margin-bottom': '2rem'}))

    if plot_sections:
        return html.Div([
            html.Br(),
            html.H3("System Monitoring Plots", style=css.STYLE_H3),
            html.Div(plot_sections)
        ])

    return None


def _create_benchmark_section(benchmark, configurations, args):
    """Create a complete benchmark section with all subsections."""
    benchmark_display = benchmark.replace('_', ' ').title()
    section_components = [html.H2(f"Benchmark: {benchmark_display}", style=css.STYLE_H2_SECTION)]

    shared_info, different_info = find_shared_and_different_info(configurations)

    differences_table = create_differences_comparison_table(configurations, different_info)
    section_components.extend([
        html.H3("Configuration Differences & Results", style=css.STYLE_H3),
        differences_table,
        html.Br()
    ])

    shared_section = create_shared_info_section(shared_info, configurations)
    section_components.extend([
        html.H3("Shared Configuration", style=css.STYLE_H3),
        shared_section,
        html.Br()
    ])

    technical_details = create_technical_details_section(configurations)
    section_components.append(technical_details)

    plots = create_plots_section(configurations, args)
    if plots:
        section_components.append(plots)

    return html.Div(section_components, style=css.STYLE_COMPARISON_SECTION)


def generate_comparison_report(report_components, configurations_by_benchmark, args):
    """Generate the main comparison report with all benchmark sections."""
    if not configurations_by_benchmark:
        report_components.append(
            html.Div("No configurations found for comparison", style=css.STYLE_ERROR_MESSAGE)
        )
        return

    for benchmark, configurations in configurations_by_benchmark.items():
        if len(configurations) < 2:
            continue

        benchmark_section = _create_benchmark_section(benchmark, configurations, args)
        report_components.append(benchmark_section)
