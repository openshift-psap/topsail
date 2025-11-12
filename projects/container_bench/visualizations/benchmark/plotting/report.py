import itertools
from dash import html, dcc
import json
import matrix_benchmarking.plotting.table_stats as table_stats
import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report
import projects.matrix_benchmarking.visualizations.helpers.plotting.styles_css as css
import projects.matrix_benchmarking.visualizations.helpers.plotting.html as html_elements
from .utils.config import GetInfo
from .utils.shared import (
    MIN_PLOT_BENCHMARK_TIME,
    SYSTEM_INFO_FIELD_MAPPINGS,
    ENGINE_INFO_FIELD_MAPPINGS,
    format_benchmark_title,
    create_host_info_items,
    create_engine_info_items,
    create_summary_info_card,
    format_field_value,
    detect_linux_system,
    detect_windows_system
)

STYLE_TITLE = {
    'font-weight': '600',
    'color': '#6c757d',
    'margin-bottom': '0.5rem'
}

STYLE_VALUE = {
    'font-size': '2rem',
    'font-weight': '300',
    'color': '#007BFF'
}

STYLE_FILEIO_VALUE = {
    'font-size': '1.5rem',
    'font-weight': '300',
    'color': '#007BFF',
    'margin': '0.3rem 0'
}

STYLE_FILEIO_LABEL = {
    'font-size': '0.9rem',
    'font-weight': '600',
    'color': '#6c757d',
    'text-transform': 'uppercase',
    'letter-spacing': '0.05em'
}

STYLE_ERROR = {
    'font-size': '1.5rem',
    'font-weight': '300',
    'color': '#dc3545'
}

STYLE_TIMESTAMP = {
    'font-size': '0.875rem',
    'color': '#6c757d',
    'margin-top': '0.5rem'
}

STYLE_CARD = {
    'background': 'white',
    'padding': '1.5rem',
    'border-radius': '8px',
    'box-shadow': '0 2px 8px rgba(0,0,0,0.08)',
    'text-align': 'center'
}

STYLE_FILEIO_SECTION = {'margin-bottom': '0.5rem'}


def register():
    BenchmarkReport()


def generate_host_items(system_info):
    base_items = create_host_info_items(system_info, SYSTEM_INFO_FIELD_MAPPINGS)

    is_windows = detect_windows_system(system_info)
    if is_windows:
        base_items = [(name, value, False, highlight) for name, value, _, highlight in base_items
                      if name != SYSTEM_INFO_FIELD_MAPPINGS["OS_version"]]
        os_version_item = (SYSTEM_INFO_FIELD_MAPPINGS["OS_version"],
                           system_info.get('OS_version', 'N/A'), True, False)
        base_items.append(os_version_item)
    else:
        base_items = [(name, value, False, highlight) for name, value, _, highlight in base_items
                      if name != SYSTEM_INFO_FIELD_MAPPINGS["Kernel_version"]]
        kernel_version_item = (SYSTEM_INFO_FIELD_MAPPINGS["Kernel_version"],
                               system_info.get('Kernel_version', 'N/A'), True, False)
        base_items.append(kernel_version_item)

    return base_items


def generate_engine_items(container_engine_info, system_info, provider_info):
    is_linux = detect_linux_system(system_info)

    # Filter out Client_version for Linux systems
    filtered_engine_mappings = ENGINE_INFO_FIELD_MAPPINGS.copy()
    if is_linux:
        filtered_engine_mappings = {k: v for k, v in ENGINE_INFO_FIELD_MAPPINGS.items() if k != "Client_version"}

    engine_items = create_engine_info_items(
        container_engine_info,
        provider_info if not is_linux else None,
        filtered_engine_mappings
    )

    formatted_items = []
    for i, (name, value, is_last, highlight) in enumerate(engine_items):
        field_key = None
        for key, display_name in ENGINE_INFO_FIELD_MAPPINGS.items():
            if display_name == name:
                field_key = key
                break

        formatted_value = format_field_value(field_key, value) if field_key else value
        formatted_items.append((name, formatted_value, is_last, highlight))

    return formatted_items


def _create_fileio_card_content(benchmark_title, read_throughput, write_throughput):
    return [
        html.Div(benchmark_title, style=STYLE_TITLE),
        html.Div([
            html.Div([
                html.Div("Read", style=STYLE_FILEIO_LABEL),
                html.Div(f"{read_throughput:.2f} MiB/s", style=STYLE_FILEIO_VALUE)
            ], style=STYLE_FILEIO_SECTION),
            html.Div([
                html.Div("Write", style=STYLE_FILEIO_LABEL),
                html.Div(f"{write_throughput:.2f} MiB/s", style=STYLE_FILEIO_VALUE)
            ])
        ])
    ]


def _create_standard_card_content(benchmark_title, benchmark_value, benchmark_unit):
    value_display = f"{benchmark_value:.2f}"
    if benchmark_unit:
        value_display = f"{benchmark_value:.2f} {benchmark_unit}"

    return [
        html.Div(benchmark_title, style=STYLE_TITLE),
        html.Div(value_display, style=STYLE_VALUE)
    ]


def _create_error_card_content(benchmark_title):
    return [
        html.Div(benchmark_title, style=STYLE_TITLE),
        html.Div("No result available", style=STYLE_ERROR)
    ]


def generate_one_benchmark_report(report_components, settings, benchmark, args):
    info = GetInfo(settings)
    if not info:
        return

    container_engine_info = info.get("container_engine_info", {})
    system = info.get("system", {})

    report_components.extend([
        html.H2(f"Benchmark: {format_benchmark_title(benchmark)}", style=css.STYLE_H2_SECTION),
    ])

    body = []

    if info.get('metric_type') == 'synthetic_benchmark':
        benchmark_value = info.get('benchmark_value')
        benchmark_title = info.get('benchmark_title', 'Result')
        benchmark_type = info.get('benchmark_type', '')
        benchmark_unit = info.get('benchmark_unit', '')
        read_throughput = info.get('benchmark_read_throughput')
        write_throughput = info.get('benchmark_write_throughput')
        timestamp = info.get('timestamp')

        if 'fileio' in benchmark_type and read_throughput is not None and write_throughput is not None:
            card_content = _create_fileio_card_content(benchmark_title, read_throughput, write_throughput)
        elif benchmark_value is not None:
            card_content = _create_standard_card_content(benchmark_title, benchmark_value, benchmark_unit)
        else:
            card_content = _create_error_card_content(benchmark_title)

        if timestamp:
            card_content.append(
                html.Div(f"Timestamp: {timestamp}", style=STYLE_TIMESTAMP)
            )

        result_card = html.Div([
            html.Div(card_content, style=STYLE_CARD)
        ], style={'margin-bottom': '2rem'})
        body.append(result_card)

    if info.get('metric_type') == 'synthetic_benchmark':
        benchmark_log = info.get('benchmark_full_log', '')
        if benchmark_log:
            log_section = html.Details([
                html.Summary(
                    'Click for Full Benchmark Log',
                    style=css.STYLE_DETAILS_SUMMARY
                ),
                html.Div([
                    html.H4("Benchmark Output", style=css.STYLE_H4),
                    html.Pre(
                        benchmark_log,
                        style=css.STYLE_JSON_PRE
                    )
                ], style=css.STYLE_DETAILS_CONTENT)
            ], style=css.STYLE_DETAILS)
            body.append(log_section)

    host_items = generate_host_items(system)
    engine_items = generate_engine_items(
        container_engine_info,
        system,
        info.get('container_engine_provider', 'N/A')
    )

    info_section_parts = []
    if info.get('metric_type') == 'container_bench':
        summary_row = html.Div([
            create_summary_info_card(info, "Benchmark Summary")
        ], style=css.STYLE_INFO_ROW)
        info_section_parts.append(summary_row)

    system_row = html.Div([
        html_elements.info_card("Host System Information", host_items),
        html_elements.info_card("Container Engine Information", engine_items)
    ], style=css.STYLE_INFO_ROW)
    info_section_parts.append(system_row)

    info_section = html.Div(info_section_parts)
    body.append(info_section)

    if info.get('execution_time_95th_percentile', 0) > MIN_PLOT_BENCHMARK_TIME:  # Only show plots for longer benchmarks
        plot_names = [
            "System CPU Usage",
            "System Memory Usage",
            "System Network Usage",
            "System Disk Usage"
        ]

        plot_cards = [
            html_elements.plot_card(name, report.set_config(dict(current_settings=settings), args))
            for name in plot_names
        ]

        plots_section = html.Div([
            html.H2("Benchmark Plots", style=css.STYLE_H2_SECTION),
            html.Div(plot_cards, style=css.STYLE_PLOTS_GRID, className='plots-grid-responsive')
        ])

        body.append(plots_section)

    details_section = html.Details([
        html.Summary('Click for Full Technical Details', style=css.STYLE_DETAILS_SUMMARY),
        html.Div([
            html.H4("Full Container Engine Information", style=css.STYLE_H4),
            html.Pre(
                json.dumps(info.get("container_engine_full", {}), indent=2),
                style=css.STYLE_JSON_PRE
            )
        ], style=css.STYLE_DETAILS_CONTENT)
    ], style=css.STYLE_DETAILS)

    body.append(details_section)
    report_components.extend([
        html.Div(body, style=css.STYLE_BENCHMARK_SECTION)
    ])


class BenchmarkReport():
    def __init__(self):
        self.name = "report: Benchmark Report"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        """Generate the complete benchmark report using improved HTML components."""
        ordered_vars, settings, setting_lists, variables, cfg = args

        report_components = [
            dcc.Markdown(f'<style>{css.EMBEDDED_CSS}</style>', dangerously_allow_html=True),
            html.H1("Container Engine Benchmark Results", style=css.STYLE_H1)
        ]
        static_settings = {k: v for k, v in settings.items() if v != "---"}

        for settings_values in sorted(itertools.product(*setting_lists), key=lambda x: x[0][0] if x else None):
            current_settings = dict(settings_values)
            current_settings.update(static_settings)
            current_settings.pop("stats", None)
            current_settings.pop("test_mac_ai", None)

            benchmark = current_settings.get("benchmark", "unknown")

            generate_one_benchmark_report(report_components, current_settings, benchmark, args)

        return None, html.Div(report_components, style=css.STYLE_CONTAINER, className='report-container')
