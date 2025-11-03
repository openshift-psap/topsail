from dash import html
import projects.matrix_benchmarking.visualizations.helpers.plotting.styles_css as css
import projects.matrix_benchmarking.visualizations.helpers.plotting.units as units
import projects.matrix_benchmarking.visualizations.helpers.plotting.html as html_elements

SYSTEM_INFO_FIELD_MAPPINGS = {
    "Model_id": "Model ID",
    "CPU_model": "CPU Model",
    "CPU_cores": "CPU Cores",
    "Architecture": "Architecture",
    "Memory": "Memory",
    "OS_version": "OS Version",
    "Kernel_version": "Kernel Version"
}

ENGINE_INFO_FIELD_MAPPINGS = {
    "Client_version": "Client Version",
    "Host_version": "Host Version",
    "Mode": "Rootless Mode",
    "Runtime": "Runtime",
    "Host_cpu": "Host CPU",
    "Host_memory": "Host Memory",
    "Host_kernel": "Host Kernel"
}


MIN_PLOT_BENCHMARK_TIME = 5  # Minimum execution time (seconds) to show plots
FASTEST_INDICATOR = "⚡ FASTEST"
LOWEST_INDICATOR = "🔽 LOWEST"
HIGHEST_INDICATOR = "🔼 HIGHEST"

DELTA_LABEL = "Performance Delta"
DELTA_TIME_LABEL = "Δ"

SUCCESS_COLOR = '#28a745'
DANGER_COLOR = '#dc3545'
MUTED_COLOR = '#6c757d'
LIGHT_BG_COLOR = '#f8f9fa'

DELTA_CELL_STYLE = {
    'font-weight': 'bold',
    'background': LIGHT_BG_COLOR
}

HIGHLIGHT_STYLE = {
    'color': SUCCESS_COLOR,
    'font-weight': 'bold'
}

CODE_STYLE = {
    'font-size': '0.85rem',
    'word-break': 'break-all'
}


def format_field_value(field_key, value):
    if field_key == "Host_memory" and value != "N/A":
        try:
            return units.human_readable_size(int(value))
        except (TypeError, ValueError):
            pass
    return value


def create_table_header(headers):
    header_cells = [html.Th(header, style=css.STYLE_TABLE_HEADER) for header in headers]
    return html.Tr(header_cells)


def create_config_cell(display_label):
    return html.Td(display_label, style={
        **css.STYLE_TABLE_CELL,
        'font-weight': 'bold',
        'background': LIGHT_BG_COLOR
    })


def create_standard_cell(content, is_highlighted=False):
    style = css.STYLE_TABLE_CELL_HIGHLIGHT if is_highlighted else css.STYLE_TABLE_CELL
    return html.Td(content, style=style)


def create_na_cell():
    return html.Td("N/A", style=css.STYLE_TABLE_CELL)


def create_execution_time_content(exec_time_95th_percentile, jitter, is_fastest=False, fastest_style=FASTEST_INDICATOR):
    if not exec_time_95th_percentile:
        return "N/A"

    content = [
        html.Span(
            f"{units.format_duration(exec_time_95th_percentile)}",
            style=css.STYLE_INFO_VALUE_HIGHLIGHT
        ),
        html.Br(),
        html.Small(
            f"(Jitter +- {units.format_duration(jitter)})",
            style=css.STYLE_SMALL_TEXT
        )
    ]

    if is_fastest:
        content.extend([
            html.Br(),
            html.Small(fastest_style, style=HIGHLIGHT_STYLE)
        ])

    return content


def create_delta_content(delta_value, delta_percentage, unit="", is_time=False):
    if is_time:
        delta_text = f"{DELTA_TIME_LABEL} {units.format_duration(delta_value)}"
    else:
        delta_text = f"{DELTA_TIME_LABEL} {delta_value:.2f} {unit}" if unit else f"{DELTA_TIME_LABEL} {delta_value:.2f}"

    return [
        html.Span(delta_text, style={'font-weight': 'bold'}),
        html.Br(),
        html.Small(f"({delta_percentage:.1f}% difference)", style={'color': MUTED_COLOR})
    ]


def create_summary_items(info, include_exec_time=True):
    summary_items = []

    if info.get('command') and info['command'] != 'N/A':
        summary_items.append(("Command", html.Code(info['command']), False, False))

    if info.get('timestamp') and info['timestamp'] != 'N/A':
        summary_items.append(("Timestamp", info['timestamp'], False, False))

    if include_exec_time and info.get('execution_time_95th_percentile'):
        exec_time_content = [
            html.Span(
                f"{units.format_duration(info['execution_time_95th_percentile'])}",
                style=css.STYLE_INFO_VALUE_HIGHLIGHT
            ),
            html.Br(),
            html.Small(
                f"(Jitter +- {units.format_duration(info.get('jitter', 0))})",
                style=css.STYLE_SMALL_TEXT
            )
        ]
        summary_items.append(("Execution Time (95th Percentile)", exec_time_content, False, True))

    if summary_items:
        last_item = summary_items[-1]
        summary_items[-1] = (last_item[0], last_item[1], True, last_item[3])

    return summary_items


def create_summary_info_card(info, title="Benchmark Summary", include_exec_time=True):
    if not info:
        return None

    summary_items = create_summary_items(info, include_exec_time)
    if summary_items:
        return html_elements.info_card(title, summary_items)
    return None


def create_host_info_card(system_info, title="Host System Information", field_mappings=None):
    if not system_info:
        return None

    mappings = field_mappings or SYSTEM_INFO_FIELD_MAPPINGS
    host_items = create_host_info_items(system_info, mappings)
    if host_items:
        return html_elements.info_card(title, host_items)
    return None


def create_engine_info_card(engine_info, title="Container Engine Information", provider_info=None, field_mappings=None):
    if not engine_info:
        return None

    mappings = field_mappings or ENGINE_INFO_FIELD_MAPPINGS
    engine_items = create_engine_info_items(engine_info, provider_info, mappings)
    if engine_items:
        return html_elements.info_card(title, engine_items)
    return None


def format_benchmark_title(benchmark):
    return benchmark.replace('_', ' ').title()


def has_long_running_benchmarks(configurations):
    return any(config.get('execution_time_95th_percentile', 0) > MIN_PLOT_BENCHMARK_TIME for config in configurations)


def create_code_cell(command):
    if command == "N/A":
        return create_standard_cell(command)
    return create_standard_cell(html.Code(command, style=CODE_STYLE))


def finalize_info_items(items):
    if items:
        last_item = items[-1]
        items[-1] = (last_item[0], last_item[1], True, last_item[3])
    return items


def create_host_info_items(system_info, field_mappings):
    host_items = []
    for field_key, field_display in field_mappings.items():
        value = system_info.get(field_key)
        if value and value != "N/A":
            host_items.append((field_display, value, False, False))
    return finalize_info_items(host_items)


def create_engine_info_items(engine_info, provider_info, field_mappings):
    engine_items = []
    engine_field_map = {"Container_engine_platform": "Engine", **field_mappings}

    for field_key, field_display in engine_field_map.items():
        value = engine_info.get(field_key)
        if value is not None and value != "N/A":
            engine_items.append((field_display, value, False, False))

    if provider_info and provider_info != "N/A":
        engine_items.append(("Provider", provider_info, False, False))

    return finalize_info_items(engine_items)


def detect_linux_system(system_info):
    return "linux" in system_info.get("OS_version", "").lower()


def detect_windows_system(system_info):
    return "windows" in system_info.get("OS_version", "").lower()


def detect_macos_system(system_info):
    os_version = system_info.get("OS_version", "").lower()
    return "mac" in os_version or "darwin" in os_version


def get_system_type(system_info):
    if detect_linux_system(system_info):
        return 'linux'
    elif detect_windows_system(system_info):
        return 'windows'
    elif detect_macos_system(system_info):
        return 'macos'
    else:
        return 'unknown'
