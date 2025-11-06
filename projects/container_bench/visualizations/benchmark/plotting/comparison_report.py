from dash import html, dcc
import json
import matrix_benchmarking.plotting.table_stats as table_stats
import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report
import projects.matrix_benchmarking.visualizations.helpers.plotting.styles_css as css
import projects.matrix_benchmarking.visualizations.helpers.plotting.html as html_elements
from .utils.config import (
    find_shared_and_different_info,
    get_all_configuration_info,
    generate_display_config_label
)

from .utils.shared import (
    MIN_PLOT_BENCHMARK_TIME,
    DELTA_LABEL,
    DELTA_CELL_STYLE,
    ENGINE_INFO_FIELD_MAPPINGS,
    SYSTEM_INFO_FIELD_MAPPINGS,
    create_table_header,
    create_config_cell,
    create_execution_time_content,
    create_delta_content,
    create_code_cell,
    format_benchmark_title,
    has_long_running_benchmarks,
    create_summary_info_card,
    create_host_info_card,
    create_engine_info_card,
)


def _get_fileio_sort_key(config):
    return (config.get("benchmark_read_throughput") or 0) + \
           (config.get("benchmark_write_throughput") or 0)


def _get_standard_sort_key(config):
    return config.get("benchmark_value") or 0


def _create_fileio_table_rows(sorted_configurations):
    valid_read_values = [
        c.get("benchmark_read_throughput")
        for c in sorted_configurations
        if c.get("benchmark_read_throughput") is not None
    ]
    valid_write_values = [
        c.get("benchmark_write_throughput")
        for c in sorted_configurations
        if c.get("benchmark_write_throughput") is not None
    ]
    best_read = max(valid_read_values) if valid_read_values else 0
    best_write = max(valid_write_values) if valid_write_values else 0

    rows = []
    for config in sorted_configurations:
        display_config_label = generate_display_config_label(config, sorted_configurations)
        read_value = config.get("benchmark_read_throughput")
        write_value = config.get("benchmark_write_throughput")
        timestamp = config.get("timestamp", "N/A")

        is_best_read = (read_value == best_read and
                        len(sorted_configurations) > 1 and
                        read_value is not None)
        is_best_write = (write_value == best_write and
                         len(sorted_configurations) > 1 and
                         write_value is not None)

        row_cells = [
            create_config_cell(display_config_label),
            html.Td(
                f"{read_value:.2f}" if read_value is not None else "N/A",
                style=css.STYLE_TABLE_CELL_HIGHLIGHT if is_best_read else css.STYLE_TABLE_CELL
            ),
            html.Td(
                f"{write_value:.2f}" if write_value is not None else "N/A",
                style=css.STYLE_TABLE_CELL_HIGHLIGHT if is_best_write else css.STYLE_TABLE_CELL
            ),
            html.Td(
                str(timestamp) if timestamp else "N/A",
                style=css.STYLE_TABLE_CELL
            )
        ]
        rows.append(html.Tr(row_cells))

    return rows


def _create_standard_table_rows(sorted_configurations, best_value):
    rows = []
    for config in sorted_configurations:
        display_config_label = generate_display_config_label(config, sorted_configurations)
        benchmark_value = config.get("benchmark_value")
        benchmark_unit = config.get("benchmark_unit", "")
        timestamp = config.get("timestamp", "N/A")

        is_best = (benchmark_value is not None and
                   benchmark_value == best_value and
                   len(sorted_configurations) > 1 and
                   benchmark_value > 0)

        if benchmark_value is not None:
            value_display = f"{benchmark_value:.2f}"
            if benchmark_unit:
                value_display = f"{benchmark_value:.2f} {benchmark_unit}"
        else:
            value_display = "N/A"

        row_cells = [
            create_config_cell(display_config_label),
            html.Td(
                value_display,
                style=css.STYLE_TABLE_CELL_HIGHLIGHT if is_best else css.STYLE_TABLE_CELL
            ),
            html.Td(
                str(timestamp) if timestamp else "N/A",
                style=css.STYLE_TABLE_CELL
            )
        ]
        rows.append(html.Tr(row_cells))

    return rows


def create_performance_delta_row(sorted_configurations, fastest_time):
    valid_times = [
        c.get("execution_time_95th_percentile", 0)
        for c in sorted_configurations
        if c.get("execution_time_95th_percentile", 0) > 0
    ]
    if len(valid_times) <= 1:
        return None

    slowest_time = max(valid_times)
    delta = slowest_time - fastest_time
    delta_percentage = ((slowest_time - fastest_time) / fastest_time) * 100 if fastest_time > 0 else 0

    return [
        html.Td(DELTA_LABEL, style={**css.STYLE_TABLE_CELL, **DELTA_CELL_STYLE}),
        html.Td(
            create_delta_content(delta, delta_percentage, is_time=True),
            style=css.STYLE_TABLE_CELL
        ),
        html.Td("-", style=css.STYLE_TABLE_CELL),
        html.Td("-", style=css.STYLE_TABLE_CELL)
    ]


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
        ordered_vars, settings, setting_lists, variables, cfg = args

        report_components = [
            dcc.Markdown(f'<style>{css.EMBEDDED_CSS}{css.COMPARISON_CSS}</style>', dangerously_allow_html=True),
            html.H1("Container Engine Benchmark Comparison", style=css.STYLE_H1)
        ]
        configurations_by_benchmark = get_all_configuration_info(settings, setting_lists)

        if configurations_by_benchmark:
            generate_comparison_report(report_components, configurations_by_benchmark, args)
        else:
            report_components.append(
                html.Div("No configuration data found for comparison", style=css.STYLE_ERROR_MESSAGE)
            )
        if len(report_components) <= 2:
            return None, html.Div("There is nothing to compare", style=css.STYLE_ERROR_MESSAGE)

        return None, html.Div(report_components, style=css.STYLE_CONTAINER, className='report-container')


def create_shared_info_section(shared_info):
    cards = []

    summary_card = create_summary_info_card(shared_info, "Benchmark Summary", include_exec_time=False)
    if summary_card:
        cards.append(summary_card)

    host_card = create_host_info_card(
        shared_info.get("system"),
        title="Host System Information",
        field_mappings=SYSTEM_INFO_FIELD_MAPPINGS
    )
    if host_card:
        cards.append(host_card)

    # Filter out Client_version for Linux systems
    system_info = shared_info.get("system", {})
    is_linux = "linux" in system_info.get("OS_version", "").lower()
    filtered_engine_mappings = ENGINE_INFO_FIELD_MAPPINGS.copy()
    if is_linux:
        filtered_engine_mappings = {k: v for k, v in ENGINE_INFO_FIELD_MAPPINGS.items() if k != "Client_version"}

    engine_card = create_engine_info_card(
        shared_info.get("engine"),
        title="Container Engine Information",
        provider_info=shared_info.get("container_engine_provider") if not is_linux else None,
        field_mappings=filtered_engine_mappings
    )
    if engine_card:
        cards.append(engine_card)

    if cards:
        return html.Div(cards, style=css.STYLE_INFO_ROW)
    else:
        return html.Div("No shared configuration information found")


def create_synthetic_benchmark_comparison_table(configurations):
    if not configurations:
        return None

    if not configurations[0].get("metric_type") == "synthetic_benchmark":
        return None

    benchmark_title = configurations[0].get("benchmark_title", "Result")
    benchmark_type = configurations[0].get("benchmark_type", "")

    is_fileio = 'fileio' in benchmark_type

    if is_fileio:
        sorted_configurations = sorted(configurations, key=_get_fileio_sort_key, reverse=True)
        headers = ["Configuration", "Read (MiB/s)", "Write (MiB/s)", "Timestamp"]
    else:
        sorted_configurations = sorted(configurations, key=_get_standard_sort_key, reverse=True)
        headers = ["Configuration", benchmark_title, "Timestamp"]

    rows = [create_table_header(headers)]

    if is_fileio:
        rows.extend(_create_fileio_table_rows(sorted_configurations))
    else:
        valid_values = [
            c.get("benchmark_value")
            for c in sorted_configurations
            if c.get("benchmark_value") is not None and c.get("benchmark_value") > 0
        ]
        best_value = max(valid_values) if valid_values else 0
        rows.extend(_create_standard_table_rows(sorted_configurations, best_value))

    return html.Table(rows, style=css.STYLE_COMPARISON_TABLE)


def create_performance_comparison_table(configurations):
    if not configurations:
        return None

    sorted_configurations = sorted(configurations, key=lambda config: config.get("execution_time_95th_percentile", 0))

    rows = []

    headers = ["Configuration", "Execution Time (95th Percentile)", "Command", "Timestamp"]
    header_row = create_table_header(headers)
    rows.append(header_row)

    valid_times = [
        c.get("execution_time_95th_percentile", 0)
        for c in sorted_configurations
        if c.get("execution_time_95th_percentile", 0) > 0
    ]
    fastest_time = min(valid_times) if valid_times else 0

    for config in sorted_configurations:
        display_config_label = generate_display_config_label(config, sorted_configurations)
        exec_time_95th_percentile = config.get("execution_time_95th_percentile", 0)
        jitter = config.get("jitter", 0)
        jitter = jitter if jitter is not None else 0

        command = config.get("command", "N/A")
        timestamp = config.get("timestamp", "N/A")

        is_fastest = (exec_time_95th_percentile == fastest_time and
                      len(sorted_configurations) > 1 and
                      exec_time_95th_percentile > 0)

        time_content = create_execution_time_content(exec_time_95th_percentile, jitter, is_fastest)

        row_cells = [
            create_config_cell(display_config_label),

            html.Td(
                time_content,
                style=css.STYLE_TABLE_CELL_HIGHLIGHT if is_fastest else css.STYLE_TABLE_CELL
            ),

            create_code_cell(command),

            html.Td(timestamp, style=css.STYLE_TABLE_CELL)
        ]

        rows.append(html.Tr(row_cells))

    delta_row_cells = create_performance_delta_row(sorted_configurations, fastest_time)
    if delta_row_cells:
        rows.append(html.Tr(delta_row_cells))

    return html.Table(rows, style=css.STYLE_COMPARISON_TABLE)


def create_differences_comparison_table(configurations):
    if not configurations or len(configurations) < 2:
        return html.Div("No differences found between configurations")

    tables = []

    if configurations[0].get("metric_type") == "synthetic_benchmark":
        synthetic_table = create_synthetic_benchmark_comparison_table(configurations)
        if synthetic_table:
            tables.append(html.Div([
                html.H4("Benchmark Results", style=css.STYLE_H4),
                synthetic_table
            ]))
    else:
        # Regular container_bench metrics
        perf_table = create_performance_comparison_table(configurations)
        if perf_table:
            tables.append(html.Div([
                html.H4("Performance Metrics", style=css.STYLE_H4),
                perf_table
            ]))

    if tables:
        return html.Div([table for table in tables if table], style={'margin-bottom': '1rem'})
    else:
        return html.Div("No differences found between configurations")


def create_benchmark_log_section(configurations):
    if not configurations:
        return None

    if configurations[0].get("metric_type") != "synthetic_benchmark":
        return None

    log_sections = []
    for _, config in enumerate(configurations):
        benchmark_log = config.get("benchmark_full_log", "")
        if not benchmark_log:
            continue

        display_config_label = generate_display_config_label(config, configurations)

        log_sections.append(html.Div([
            html.H5(f"{display_config_label}", style=css.STYLE_H4),
            html.Pre(
                benchmark_log,
                style=css.STYLE_JSON_PRE
            )
        ], style={'margin-bottom': '1rem'}))

    if not log_sections:
        return None

    return html.Details([
        html.Summary('Click for Full Benchmark Logs', style=css.STYLE_DETAILS_SUMMARY),
        html.Div(log_sections, style=css.STYLE_DETAILS_CONTENT)
    ], style=css.STYLE_DETAILS)


def create_technical_details_section(configurations):
    if not configurations:
        return None

    details_sections = []
    for _, config in enumerate(configurations):
        container_engine_full = config.get("container_engine_full", {})
        display_config_label = generate_display_config_label(config, configurations)

        details_sections.append(html.Div([
            html.H5(f"{display_config_label}", style=css.STYLE_H4),
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

    has_long_benchmarks = has_long_running_benchmarks(configurations)

    if not has_long_benchmarks:
        return None

    plot_names = [
        "System CPU Usage",
        "System Memory Usage",
        "System Network Usage",
        "System Disk Usage"
    ]

    plot_sections = []
    for config in configurations:
        if config.get('execution_time_95th_percentile', 0) > MIN_PLOT_BENCHMARK_TIME:
            settings = config.get("settings", {})

            plot_cards = [
                html_elements.plot_card(name, report.set_config(dict(current_settings=settings), args))
                for name in plot_names
            ]
            display_config_label = generate_display_config_label(config, configurations)
            plot_sections.append(html.Div([
                html.H5(f"{display_config_label} - System Monitoring", style=css.STYLE_H4),
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
    benchmark_display = format_benchmark_title(benchmark)
    section_components = [html.H2(f"Benchmark: {benchmark_display}", style=css.STYLE_H2_SECTION)]

    shared_info, _ = find_shared_and_different_info(configurations)

    differences_table = create_differences_comparison_table(configurations)
    section_components.extend([
        html.H3("Configuration Differences & Results", style=css.STYLE_H3),
        differences_table,
        html.Br()
    ])

    benchmark_logs = create_benchmark_log_section(configurations)
    if benchmark_logs:
        section_components.append(benchmark_logs)

    shared_section = create_shared_info_section(shared_info)
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
