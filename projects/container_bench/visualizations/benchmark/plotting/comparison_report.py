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
from .utils.metrics import (
    METRIC_DISPLAY_CONFIG,
    calculate_config_metrics,
    calculate_usage_deltas
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
    create_metric_value_cell,
    create_delta_content,
    create_code_cell,
    format_benchmark_title,
    has_long_running_benchmarks,
    create_usage_table_headers,
    create_summary_info_card,
    create_host_info_card,
    create_engine_info_card,
)


def create_performance_delta_row(sorted_configurations, fastest_time):
    valid_times = [c.get("exec_time", 0) for c in sorted_configurations if c.get("exec_time", 0) > 0]
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


def create_shared_info_section(shared_info, configurations):
    cards = []

    summary_card = create_summary_info_card(shared_info, "Benchmark Summary", include_exec_time=False)
    if summary_card:
        cards.append(summary_card)

    host_card = create_host_info_card(shared_info.get("system"), SYSTEM_INFO_FIELD_MAPPINGS)
    if host_card:
        cards.append(host_card)

    engine_card = create_engine_info_card(
        shared_info.get("engine"),
        shared_info.get("container_engine_provider"),
        ENGINE_INFO_FIELD_MAPPINGS
    )
    if engine_card:
        cards.append(engine_card)

    if cards:
        return html.Div(cards, style=css.STYLE_INFO_ROW)
    else:
        return html.Div("No shared configuration information found")


def create_performance_comparison_table(configurations):
    if not configurations:
        return None

    sorted_configurations = sorted(configurations, key=lambda config: config.get("exec_time", 0))

    rows = []

    headers = ["Configuration", "Execution Time", "Command", "Timestamp"]
    header_row = create_table_header(headers)
    rows.append(header_row)

    valid_times = [c.get("exec_time", 0) for c in sorted_configurations if c.get("exec_time", 0) > 0]
    fastest_time = min(valid_times) if valid_times else 0

    for config in sorted_configurations:
        display_config_label = generate_display_config_label(config, sorted_configurations)
        exec_time = config.get("exec_time", 0)
        runs = config.get("runs", 1)
        command = config.get("command", "N/A")
        timestamp = config.get("timestamp", "N/A")

        is_fastest = (exec_time == fastest_time and
                      len(sorted_configurations) > 1 and
                      exec_time > 0)

        time_content = create_execution_time_content(exec_time, runs, is_fastest)

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


def create_average_usage_comparison_table(configurations):
    if not configurations:
        return None

    has_metrics = any(config.get('exec_time', 0) > MIN_PLOT_BENCHMARK_TIME for config in configurations)
    if not has_metrics:
        return None

    sorted_configurations = sorted(configurations, key=lambda config: config.get("exec_time", 0))

    config_metrics = {}
    for config in sorted_configurations:
        config_label = config.get("config_label", "Unknown")
        settings = config.get("settings", {})
        config_metrics[config_label] = calculate_config_metrics(settings)

    if not any(config_metrics.values()):
        return None

    rows = []

    headers = create_usage_table_headers(METRIC_DISPLAY_CONFIG)
    header_row = create_table_header(headers)
    rows.append(header_row)

    metric_ranges = {}
    for metric_type in METRIC_DISPLAY_CONFIG.keys():
        values = []
        for config in sorted_configurations:
            config_label = config.get("config_label", "Unknown")
            metrics = config_metrics.get(config_label, {})
            value = metrics.get(metric_type)
            if value is not None:
                values.append(value)

        if values:
            min_val = min(values)
            max_val = max(values)
            metric_ranges[metric_type] = {
                'min': min_val,
                'max': max_val,
                'has_multiple': len(values) > 1 and min_val != max_val  # Check if values are actually different
            }

    for config in sorted_configurations:
        config_label = config.get("config_label", "Unknown")
        display_config_label = generate_display_config_label(config, sorted_configurations)
        metrics = config_metrics.get(config_label, {})

        row_cells = [create_config_cell(display_config_label)]

        for metric_type, (label, unit) in METRIC_DISPLAY_CONFIG.items():
            value = metrics.get(metric_type)
            if value is not None:
                # Determine if this value is min or max for highlighting
                metric_range = metric_ranges.get(metric_type, {})
                is_min = metric_range.get('has_multiple', False) and value == metric_range.get('min')
                is_max = metric_range.get('has_multiple', False) and value == metric_range.get('max')
                is_single = len(sorted_configurations) == 1

                metric_cell = create_metric_value_cell(value, unit, is_min, is_max, is_single)
                row_cells.append(metric_cell)
            else:
                row_cells.append(html.Td("N/A", style=css.STYLE_TABLE_CELL))

        rows.append(html.Tr(row_cells))

    if len(sorted_configurations) > 1:
        usage_deltas = calculate_usage_deltas(sorted_configurations)
        if usage_deltas:
            delta_cells = [create_config_cell("Performance Delta")]

            for metric_type, (label, unit) in METRIC_DISPLAY_CONFIG.items():
                if metric_type in usage_deltas:
                    delta_info = usage_deltas[metric_type]
                    delta_content = create_delta_content(
                        delta_info['delta'],
                        delta_info['percentage'],
                        unit
                    )
                    delta_cells.append(html.Td(delta_content, style=css.STYLE_TABLE_CELL))
                else:
                    delta_cells.append(html.Td("-", style=css.STYLE_TABLE_CELL))

            rows.append(html.Tr(delta_cells))

    return html.Table(rows, style=css.STYLE_COMPARISON_TABLE)


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

    usage_table = create_average_usage_comparison_table(configurations)
    if usage_table:
        tables.append(html.Div([
            html.H4("Average System Usage", style=css.STYLE_H4),
            usage_table
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
        if config.get('exec_time', 0) > MIN_PLOT_BENCHMARK_TIME:
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
