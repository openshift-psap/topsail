from dash import html, dcc
import json
import logging
import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common
import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report
import projects.matrix_benchmarking.visualizations.helpers.plotting.styles_css as css
import projects.matrix_benchmarking.visualizations.helpers.plotting.html as html_elements
import projects.matrix_benchmarking.visualizations.helpers.plotting.units as units

logging.basicConfig(level=logging.INFO)


def register():
    BenchmarkReport()


def getInfo(settings, setting_lists, benchmark_name):
    data = dict()

    for entry in common.Matrix.all_records(settings, setting_lists):

        if entry.settings.__dict__.get("benchmark") != benchmark_name:
            continue
        metrics = entry.results.__dict__.get("metrics")
        if not metrics:
            continue
        test_config = entry.results.__dict__.get("test_config", {})
        container_engine_provider = ""
        if not test_config:
            logging.warning("Missing test_config in entry results.")
        else:
            container_engine_provider = test_config.yaml_file.get(
                "prepare", {}).get(
                    "podman", {}).get(
                        "machine", {}).get(
                            "env", {}).get("CONTAINERS_MACHINE_PROVIDER", "")

        data["exec_time"] = metrics.execution_time
        data["command"] = metrics.command
        data["timestamp"] = metrics.timestamp

        data["container_engine_provider"] = container_engine_provider
        data["runs"] = entry.settings.__dict__.get("benchmark_runs", 1)

        system_state = entry.results.__dict__.get("system_state")
        if system_state:
            sys_info = dict()
            software = system_state.get("Software", {})
            system_software_overview = software.get("System Software Overview", {})
            sys_info["OS_version"] = system_software_overview.get("System Version", "")
            sys_info["Kernel_version"] = system_software_overview.get("Kernel Version", "")

            hardware = system_state.get("Hardware", {})
            hardware_overview = hardware.get("Hardware Overview", {})
            sys_info["CPU_model"] = hardware_overview.get("Chip", "")
            sys_info["CPU_cores"] = hardware_overview.get("Total Number of Cores", "")
            sys_info["Memory"] = hardware_overview.get("Memory", "")
            sys_info["Model_id"] = hardware_overview.get("Model Identifier", "")
            data["system"] = sys_info

        container_engine_info = entry.results.__dict__.get("container_engine_info")
        if container_engine_info:
            engine_info = dict()
            client = container_engine_info.get("Client", {})
            engine_info["Container_engine_platform"] = entry.settings.__dict__.get("container_engine", "")
            engine_info["Client_version"] = client.get("Version", "")
            host = container_engine_info.get("host", {})
            engine_info["Mode"] = host.get("security", {}).get("rootless", "")
            engine_info["Host_version"] = container_engine_info.get("version", {}).get("Version", "")
            engine_info["Host_cpu"] = host.get("cpus", "")
            engine_info["Host_memory"] = host.get("memTotal", "")
            engine_info["Host_kernel"] = host.get("kernel", "")
            data["container_engine_full"] = container_engine_info
            data["container_engine_info"] = engine_info

    return data


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

        for benchmark in common.Matrix.settings.get("benchmark", []):
            info = getInfo(settings, setting_lists, benchmark)
            container_engine_info = info.get("container_engine_info", {})
            system = info.get("system", {})

            report_components.extend([
                html.H2(f"Benchmark: {benchmark.replace('_', ' ')}", style=css.STYLE_H2_SECTION),
            ])

            summary_items = [
                ("Command", html.Code(info.get('command', 'N/A')), False, False),
                ("Timestamp", info.get('timestamp', 'N/A'), False, False),
                ("Execution Time", [
                    html.Span(
                        f"{units.format_duration(info.get('exec_time', 0))}",
                        style=css.STYLE_INFO_VALUE_HIGHLIGHT
                    ),
                    html.Br(),
                    html.Small(
                        f"(Average of {info.get('runs', 1)} runs)",
                        style=css.STYLE_SMALL_TEXT
                    )
                ], True, True),
            ]

            host_items = [
                ("Model ID", system.get('Model_id', 'N/A'), False, False),
                ("CPU", f"{system.get('CPU_model', 'N/A')}", False, False),
                ("Cores", f"{system.get('CPU_cores', 'N/A')}", False, False),
                ("Memory", system.get('Memory', 'N/A'), False, False),
                ("OS Version", system.get('OS_version', 'N/A'), False, False),
                ("Kernel", system.get('Kernel_version', 'N/A'), True, False),
            ]

            mem_val = container_engine_info.get('Host_memory')
            try:
                mem_display = units.human_readable_size(int(mem_val))
            except (TypeError, ValueError):
                mem_display = "N/A"

            engine_items = [
                ("Engine", container_engine_info.get('Container_engine_platform', 'N/A'), False, False),
                ("Client Version", container_engine_info.get('Client_version', 'N/A'), False, False),
                ("Provider", info.get('container_engine_provider', 'N/A'), False, False),
                ("Rootless", container_engine_info.get('Mode', 'N/A'), False, False),
                ("Host Version", container_engine_info.get('Host_version', 'N/A'), False, False),
                ("Host CPU", container_engine_info.get('Host_cpu', 'N/A'), False, False),
                ("Host Memory", mem_display, False, False),
                ("Host Kernel", container_engine_info.get('Host_kernel', 'N/A'), True, False),
            ]

            # Create info cards in rows for better readability
            summary_row = html.Div([
                html_elements.info_card("Benchmark Summary", summary_items)
            ], style=css.STYLE_INFO_ROW)

            system_row = html.Div([
                html_elements.info_card("Host System Information", host_items),
                html_elements.info_card("Container Engine Information", engine_items)
            ], style=css.STYLE_INFO_ROW)

            info_section = html.Div([
                summary_row,
                system_row
            ])

            plot_names = [
                "System CPU Usage",
                "System Power Usage",
                "System Memory Usage",
                "System Network Usage",
                "System Disk Usage"
            ]

            plot_cards = [
                html_elements.plot_card(name, report.set_config(dict(benchmark=benchmark), args))
                for name in plot_names
            ]

            plots_section = html.Div([
                html.H2("Benchmark Plots", style=css.STYLE_H2_SECTION),
                html.Div(plot_cards, style=css.STYLE_PLOTS_GRID, className='plots-grid-responsive')
            ])

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

            report_components.extend([
                html.Div([
                    info_section,
                    plots_section,
                    details_section,
                ], style=css.STYLE_BENCHMARK_SECTION)
            ])

        return None, html.Div(report_components, style=css.STYLE_CONTAINER, className='report-container')
