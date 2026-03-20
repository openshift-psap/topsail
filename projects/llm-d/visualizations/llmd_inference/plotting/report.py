from dash import html

import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    GuidellmResultsTable()
    MultiturnResultsTable()
    GuidellmPerformanceAnalysisReport()

    # Register Prometheus reports
    from . import prometheus_reports
    prometheus_reports.register()


class GuidellmResultsTable():
    def __init__(self):
        self.name = "report: GuideLLM Results Table"
        self.id_name = self.name.lower().replace(" ", "_").replace("-", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, *args):
        """
        Generate GuideLLM results tables
        """
        ordered_vars, settings, setting_lists, variables, cfg = args
        entries = list(common.Matrix.all_records(settings, setting_lists))

        header = []
        header.append(html.H2("GuideLLM Benchmark Results Tables"))
        header.append(html.Br())

        if not entries:
            header.append(html.P("No test entries found."))
            return None, header

        # Add artifact links at the top
        header.append(html.H4("🔗 Artifact Links"))
        artifact_links = []

        for i, entry in enumerate(entries):
            # Get artifacts base directory for links
            artifacts_basedir = getattr(entry.results, 'from_local_env', {})
            if hasattr(artifacts_basedir, 'artifacts_basedir'):
                artifacts_basedir = artifacts_basedir.artifacts_basedir

                # Get unique name for this entry (includes flavor info)
                entry_name = entry.get_name(variables) if variables else f"Test {i + 1}"
                artifact_links.append(html.Li([
                    html.A(f"🗂️ {entry_name} - Test artifacts directory",
                          href=str(artifacts_basedir), target="_blank")
                ]))

                # Look for specific GuideLLM benchmark directory and log file
                if hasattr(entry.results, 'guidellm_benchmarks') and entry.results.guidellm_benchmarks:
                    guidellm_dir = None
                    log_file = None

                    # Look for directory matching pattern: *__llmd__run_guidellm_benchmark
                    for item in artifacts_basedir.iterdir():
                        if item.is_dir() and '__llmd__run_guidellm_benchmark' in item.name:
                            guidellm_dir = item
                            # Log file is directly in this directory
                            potential_log = guidellm_dir / "artifacts" / "guidellm_benchmark_job.logs"
                            if potential_log.exists():
                                log_file = potential_log
                            break

                    if guidellm_dir:
                        guidellm_sublinks = [
                            html.Li(html.A("📊 GuideLLM benchmark directory",
                                          href=str(guidellm_dir), target="_blank"))
                        ]
                        if log_file:
                            guidellm_sublinks.append(
                                html.Li(html.A("📄 benchmark logs",
                                              href=str(log_file), target="_blank"))
                            )
                        artifact_links.append(html.Li([
                            "GuideLLM:",
                            html.Ul(guidellm_sublinks)
                        ]))
            else:
                # Get unique name for this entry (includes flavor info)
                entry_name = entry.get_name(variables) if variables else f"Test {i + 1}"
                artifact_links.append(html.Li(f"🗂️ {entry_name} - Artifacts not available"))

        if artifact_links:
            header.append(html.Ul(artifact_links))
        else:
            header.append(html.P("No artifact links available"))

        header.append(html.Br())

        # Collect all GuideLLM benchmarks across all entries with their configuration info
        all_benchmarks = []
        benchmark_configs = []
        for entry in entries:
            if hasattr(entry.results, 'guidellm_benchmarks') and entry.results.guidellm_benchmarks:
                # Get unique name for this entry (includes flavor info)
                entry_name = entry.get_name(variables) if variables else f"Unknown Configuration"
                for benchmark in entry.results.guidellm_benchmarks:
                    all_benchmarks.append(benchmark)
                    benchmark_configs.append(entry_name)

        if not all_benchmarks:
            header.append(html.P("No GuideLLM benchmark data found."))
            return None, header

        # Sort benchmarks by configuration first, then by request rate (best performance first)
        # Create pairs of (benchmark, config) and sort them
        benchmark_pairs = list(zip(all_benchmarks, benchmark_configs))
        benchmark_pairs.sort(key=lambda pair: (pair[1], -pair[0].request_rate))
        all_benchmarks = [pair[0] for pair in benchmark_pairs]
        benchmark_configs = [pair[1] for pair in benchmark_pairs]

        # Create performance overview table
        header.append(html.H3("📊 Performance Overview"))

        overview_headers = [
            "Configuration", "Strategy", "Request Rate (req/s)", "TTFT P50 (ms)", "TTFT P95 (ms)",
            "Latency P50 (ms)", "Latency P95 (ms)", "Tokens/s", "Concurrency"
        ]

        overview_rows = []
        for i, benchmark in enumerate(all_benchmarks):
            row = [
                benchmark_configs[i],
                benchmark.strategy,
                f"{benchmark.request_rate:.2f}",
                f"{benchmark.ttft_median:.1f}",
                f"{benchmark.ttft_p95:.1f}",
                f"{benchmark.request_latency_median * 1000:.1f}",
                f"{benchmark.request_latency_p95 * 1000:.1f}",
                f"{benchmark.tokens_per_second:.1f}",
                f"{benchmark.request_concurrency:.1f}"
            ]
            overview_rows.append(row)

        # Create HTML table
        header.append(self._create_html_table(overview_headers, overview_rows))
        header.append(html.Br())

        # Create latency breakdown table
        header.append(html.H3("⏱️ Latency Component Breakdown"))

        latency_headers = [
            "Configuration", "Strategy", "TTFT P50", "TTFT P95", "ITL P50", "ITL P95",
            "TPOT P50", "TPOT P95", "Total Latency P50", "Total Latency P95"
        ]

        latency_rows = []
        for i, benchmark in enumerate(all_benchmarks):
            row = [
                benchmark_configs[i],
                benchmark.strategy,
                f"{benchmark.ttft_median:.1f} ms",
                f"{benchmark.ttft_p95:.1f} ms",
                f"{benchmark.itl_median:.1f} ms",
                f"{benchmark.itl_p95:.1f} ms",
                f"{benchmark.tpot_median:.1f} ms",
                f"{benchmark.tpot_p95:.1f} ms",
                f"{benchmark.request_latency_median * 1000:.1f} ms",
                f"{benchmark.request_latency_p95 * 1000:.1f} ms"
            ]
            latency_rows.append(row)

        header.append(self._create_html_table(latency_headers, latency_rows))
        header.append(html.Br())

        # Create token throughput table
        header.append(html.H3("🔤 Token Throughput Analysis"))

        token_headers = [
            "Configuration", "Strategy", "Total Tokens/s", "Input Tokens/s", "Output Tokens/s",
            "Input Tokens/req", "Output Tokens/req", "Total Tokens/req"
        ]

        token_rows = []
        for i, benchmark in enumerate(all_benchmarks):
            row = [
                benchmark_configs[i],
                benchmark.strategy,
                f"{benchmark.tokens_per_second:.1f}",
                f"{benchmark.input_tokens_per_second:.1f}",
                f"{benchmark.output_tokens_per_second:.1f}",
                f"{benchmark.input_tokens_per_request:.1f}",
                f"{benchmark.output_tokens_per_request:.1f}",
                f"{benchmark.total_tokens_per_request:.1f}"
            ]
            token_rows.append(row)

        header.append(self._create_html_table(token_headers, token_rows))
        header.append(html.Br())

        # Add summary statistics
        header.append(html.H3("📈 Summary Statistics"))

        # Find best performers with their configurations
        best_throughput_idx = max(range(len(all_benchmarks)), key=lambda i: all_benchmarks[i].request_rate)
        best_latency_idx = min(range(len(all_benchmarks)), key=lambda i: all_benchmarks[i].ttft_median)
        best_tokens_idx = max(range(len(all_benchmarks)), key=lambda i: all_benchmarks[i].tokens_per_second)

        best_throughput = all_benchmarks[best_throughput_idx]
        best_latency = all_benchmarks[best_latency_idx]
        best_tokens = all_benchmarks[best_tokens_idx]

        # Configuration analysis
        configurations = {}
        for i, benchmark in enumerate(all_benchmarks):
            config = benchmark_configs[i]
            if config not in configurations:
                configurations[config] = {
                    'throughput': [],
                    'latency': [],
                    'tokens': [],
                    'count': 0
                }
            configurations[config]['throughput'].append(benchmark.request_rate)
            configurations[config]['latency'].append(benchmark.ttft_median)
            configurations[config]['tokens'].append(benchmark.tokens_per_second)
            configurations[config]['count'] += 1

        summary_stats = [
            f"🏆 Best throughput: {best_throughput.strategy} in {benchmark_configs[best_throughput_idx]} ({best_throughput.request_rate:.2f} req/s)",
            f"⚡ Best TTFT: {best_latency.strategy} in {benchmark_configs[best_latency_idx]} ({best_latency.ttft_median:.1f} ms)",
            f"🚀 Best token throughput: {best_tokens.strategy} in {benchmark_configs[best_tokens_idx]} ({best_tokens.tokens_per_second:.1f} tok/s)",
            f"📊 Total strategies tested: {len(all_benchmarks)} across {len(configurations)} configurations"
        ]

        for stat in summary_stats:
            header.append(html.P(stat))

        # Add per-configuration summary
        if len(configurations) > 1:
            header.append(html.Br())
            header.append(html.H4("🔧 Configuration Performance Comparison"))

            for config, metrics in configurations.items():
                avg_throughput = sum(metrics['throughput']) / len(metrics['throughput'])
                avg_latency = sum(metrics['latency']) / len(metrics['latency'])
                avg_tokens = sum(metrics['tokens']) / len(metrics['tokens'])

                config_summary = f"• {config}: {avg_throughput:.1f} req/s avg, {avg_latency:.1f} ms TTFT avg, {avg_tokens:.0f} tok/s avg ({metrics['count']} strategies)"
                header.append(html.P(config_summary))

        return None, header

    def _create_html_table(self, headers, rows):
        """Create an HTML table with the given headers and rows"""
        table_style = {
            "border": "1px solid #ddd",
            "border-collapse": "collapse",
            "width": "100%",
            "margin": "10px 0"
        }

        header_style = {
            "background-color": "#f2f2f2",
            "padding": "12px",
            "text-align": "left",
            "border": "1px solid #ddd",
            "font-weight": "bold"
        }

        cell_style = {
            "padding": "8px",
            "text-align": "left",
            "border": "1px solid #ddd"
        }

        # Create header row
        header_cells = [html.Th(header, style=header_style) for header in headers]
        header_row = html.Tr(header_cells)

        # Create data rows
        data_rows = []
        for i, row in enumerate(rows):
            # Alternate row colors for better readability
            row_style = {"background-color": "#f9f9f9"} if i % 2 == 0 else {}

            cells = [html.Td(cell, style={**cell_style, **row_style}) for cell in row]
            data_rows.append(html.Tr(cells))

        return html.Table([header_row] + data_rows, style=table_style)


class MultiturnResultsTable():
    def __init__(self):
        self.name = "report: Multi-turn Results Table"
        self.id_name = self.name.lower().replace(" ", "_").replace("-", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, *args):
        """
        Generate Multi-turn benchmark results tables
        """
        ordered_vars, settings, setting_lists, variables, cfg = args
        entries = list(common.Matrix.all_records(settings, setting_lists))

        header = []
        header.append(html.H2("Multi-turn Benchmark Results Tables"))
        header.append(html.Br())

        if not entries:
            header.append(html.P("No test entries found."))
            return None, header

        # Add artifact links at the top
        header.append(html.H4("🔗 Artifact Links"))
        artifact_links = []

        for i, entry in enumerate(entries):
            # Get artifacts base directory for links
            artifacts_basedir = getattr(entry.results, 'from_local_env', {})
            if hasattr(artifacts_basedir, 'artifacts_basedir'):
                artifacts_basedir = artifacts_basedir.artifacts_basedir

                # Get unique name for this entry (includes flavor info)
                entry_name = entry.get_name(variables) if variables else f"Test {i + 1}"
                artifact_links.append(html.Li([
                    html.A(f"🗂️ {entry_name} - Test artifacts directory",
                          href=str(artifacts_basedir), target="_blank")
                ]))

                # Look for specific Multi-turn benchmark directory and log file
                if hasattr(entry.results, 'multiturn_benchmark') and entry.results.multiturn_benchmark:
                    multiturn_dir = None
                    log_file = None

                    # Look for directory matching pattern: *__llmd__run_multiturn_benchmark
                    for item in artifacts_basedir.iterdir():
                        if item.is_dir() and '__llmd__run_multiturn_benchmark' in item.name:
                            multiturn_dir = item
                            # Log file is directly in this directory
                            potential_log = multiturn_dir / "artifacts" / "multiturn_benchmark_job.logs"
                            if potential_log.exists():
                                log_file = potential_log
                            break

                    if multiturn_dir:
                        multiturn_sublinks = [
                            html.Li(html.A("🔄 Multi-turn benchmark directory",
                                          href=str(multiturn_dir), target="_blank"))
                        ]
                        if log_file:
                            multiturn_sublinks.append(
                                html.Li(html.A("📄 benchmark logs",
                                              href=str(log_file), target="_blank"))
                            )
                        artifact_links.append(html.Li([
                            "Multi-turn:",
                            html.Ul(multiturn_sublinks)
                        ]))
            else:
                # Get unique name for this entry (includes flavor info)
                entry_name = entry.get_name(variables) if variables else f"Test {i + 1}"
                artifact_links.append(html.Li(f"🗂️ {entry_name} - Artifacts not available"))

        if artifact_links:
            header.append(html.Ul(artifact_links))
        else:
            header.append(html.P("No artifact links available"))

        header.append(html.Br())

        # Collect all multi-turn benchmarks across all entries
        all_benchmarks = []
        benchmark_names = []
        for i, entry in enumerate(entries):
            if hasattr(entry.results, 'multiturn_benchmark') and entry.results.multiturn_benchmark:
                benchmark = entry.results.multiturn_benchmark
                # Get unique name for this entry (includes flavor info)
                entry_name = entry.get_name(variables) if variables else f"Test {i + 1}"
                all_benchmarks.append(benchmark)
                benchmark_names.append(entry_name)

        if not all_benchmarks:
            header.append(html.P("No multi-turn benchmark data found."))
            return None, header

        # Create overall performance table
        header.append(html.H3("📊 Overall Performance Summary"))

        overall_headers = [
            "Test Run", "Total Time (s)", "Total Requests", "Conversations",
            "Completion Rate", "Requests/sec", "Avg Request Time (ms)"
        ]

        overall_rows = []
        for i, benchmark in enumerate(all_benchmarks):
            completion_rate = (benchmark.completed_conversations / benchmark.total_conversations * 100) if benchmark.total_conversations > 0 else 0
            row = [
                benchmark_names[i],
                f"{benchmark.total_time:.1f}",
                f"{benchmark.total_requests}",
                f"{benchmark.completed_conversations}/{benchmark.total_conversations}",
                f"{completion_rate:.1f}%",
                f"{benchmark.requests_per_second:.2f}",
                f"{benchmark.total_request_time_mean:.1f}"
            ]
            overall_rows.append(row)

        header.append(self._create_html_table(overall_headers, overall_rows))
        header.append(html.Br())

        # Create TTFT analysis table
        header.append(html.H3("⏱️ Time to First Token (TTFT) Analysis"))

        ttft_headers = [
            "Test Run", "TTFT Mean (ms)", "TTFT P50 (ms)", "TTFT P95 (ms)",
            "TTFT P99 (ms)", "TTFT Min (ms)", "TTFT Max (ms)", "TTFT Range (ms)"
        ]

        ttft_rows = []
        for i, benchmark in enumerate(all_benchmarks):
            ttft_range = benchmark.ttft_max - benchmark.ttft_min
            row = [
                benchmark_names[i],
                f"{benchmark.ttft_mean:.1f}",
                f"{benchmark.ttft_p50:.1f}",
                f"{benchmark.ttft_p95:.1f}",
                f"{benchmark.ttft_p99:.1f}",
                f"{benchmark.ttft_min:.1f}",
                f"{benchmark.ttft_max:.1f}",
                f"{ttft_range:.1f}"
            ]
            ttft_rows.append(row)

        header.append(self._create_html_table(ttft_headers, ttft_rows))
        header.append(html.Br())

        # Create prefix caching analysis table (if data available)
        prefix_data_available = any(
            benchmark.first_turn_avg and benchmark.later_turns_avg and benchmark.speedup_ratio
            for benchmark in all_benchmarks
        )

        if prefix_data_available:
            header.append(html.H3("🚀 Prefix Caching Performance"))

            prefix_headers = [
                "Test Run", "First Turn Avg (ms)", "Later Turns Avg (ms)",
                "Speedup Ratio", "Time Saved (%)", "Caching Benefit"
            ]

            prefix_rows = []
            for i, benchmark in enumerate(all_benchmarks):
                if benchmark.first_turn_avg and benchmark.later_turns_avg and benchmark.speedup_ratio:
                    time_saved = ((benchmark.first_turn_avg - benchmark.later_turns_avg) / benchmark.first_turn_avg * 100) if benchmark.first_turn_avg > 0 else 0
                    benefit = "🟢 Excellent" if benchmark.speedup_ratio > 2 else "🟡 Good" if benchmark.speedup_ratio > 1.5 else "🔴 Minimal"

                    row = [
                        benchmark_names[i],
                        f"{benchmark.first_turn_avg:.1f}",
                        f"{benchmark.later_turns_avg:.1f}",
                        f"{benchmark.speedup_ratio:.2f}x",
                        f"{time_saved:.1f}%",
                        benefit
                    ]
                    prefix_rows.append(row)

            if prefix_rows:
                header.append(self._create_html_table(prefix_headers, prefix_rows))
                header.append(html.Br())

        # Create TTFT by turn analysis (if data available)
        turn_data_available = any(benchmark.ttft_by_turn for benchmark in all_benchmarks)

        if turn_data_available:
            header.append(html.H3("🔄 TTFT by Turn Number"))

            # Get all unique turn numbers across all benchmarks
            all_turns = set()
            for benchmark in all_benchmarks:
                all_turns.update(benchmark.ttft_by_turn.keys())

            sorted_turns = sorted(all_turns)

            turn_headers = ["Test Run"] + [f"Turn {turn}" for turn in sorted_turns]

            turn_rows = []
            for i, benchmark in enumerate(all_benchmarks):
                row = [benchmark_names[i]]
                for turn in sorted_turns:
                    ttft = benchmark.ttft_by_turn.get(turn, 0)
                    row.append(f"{ttft:.1f} ms" if ttft > 0 else "N/A")
                turn_rows.append(row)

            header.append(self._create_html_table(turn_headers, turn_rows))
            header.append(html.Br())
            header += report.Plot_and_Text(f"Multi-turn TTFT by Turn Number", args)


        # Create TTFT by document type analysis (if data available)
        doc_type_data_available = any(benchmark.ttft_by_doc_type for benchmark in all_benchmarks)

        if doc_type_data_available:
            header.append(html.H3("📄 TTFT by Document Type"))

            # Get all unique document types across all benchmarks
            all_doc_types = set()
            for benchmark in all_benchmarks:
                all_doc_types.update(benchmark.ttft_by_doc_type.keys())

            sorted_doc_types = sorted(all_doc_types)

            doc_headers = ["Test Run"] + sorted_doc_types

            doc_rows = []
            for i, benchmark in enumerate(all_benchmarks):
                row = [benchmark_names[i]]
                for doc_type in sorted_doc_types:
                    ttft = benchmark.ttft_by_doc_type.get(doc_type, 0)
                    row.append(f"{ttft:.1f} ms" if ttft > 0 else "N/A")
                doc_rows.append(row)

            header.append(self._create_html_table(doc_headers, doc_rows))
            header.append(html.Br())

        # Add summary insights
        header.append(html.H3("📈 Key Insights"))

        if all_benchmarks:
            # Find best performers by index
            best_throughput_idx = max(range(len(all_benchmarks)), key=lambda i: all_benchmarks[i].requests_per_second)
            best_ttft_idx = min(range(len(all_benchmarks)), key=lambda i: all_benchmarks[i].ttft_p50)

            best_throughput = all_benchmarks[best_throughput_idx]
            best_ttft = all_benchmarks[best_ttft_idx]

            # Calculate average completion rate
            avg_completion = sum(
                (b.completed_conversations / b.total_conversations * 100) if b.total_conversations > 0 else 0
                for b in all_benchmarks
            ) / len(all_benchmarks)

            insights = [
                f"🏆 Best throughput: {benchmark_names[best_throughput_idx]} ({best_throughput.requests_per_second:.2f} req/s)",
                f"⚡ Best TTFT P50: {benchmark_names[best_ttft_idx]} ({best_ttft.ttft_p50:.1f} ms)",
                f"📊 Average completion rate: {avg_completion:.1f}%",
                f"🔄 Total test runs analyzed: {len(all_benchmarks)}"
            ]

            # Add prefix caching insights if available
            if prefix_data_available:
                speedup_benchmarks = [(i, b) for i, b in enumerate(all_benchmarks) if b.speedup_ratio]
                if speedup_benchmarks:
                    best_speedup_idx, best_speedup = max(speedup_benchmarks, key=lambda x: x[1].speedup_ratio)
                    insights.append(f"🚀 Best prefix caching speedup: {benchmark_names[best_speedup_idx]} ({best_speedup.speedup_ratio:.2f}x)")

            for insight in insights:
                header.append(html.P(insight))

        return None, header

    def _create_html_table(self, headers, rows):
        """Create an HTML table with the given headers and rows"""
        table_style = {
            "border": "1px solid #ddd",
            "border-collapse": "collapse",
            "width": "100%",
            "margin": "10px 0"
        }

        header_style = {
            "background-color": "#f2f2f2",
            "padding": "12px",
            "text-align": "left",
            "border": "1px solid #ddd",
            "font-weight": "bold"
        }

        cell_style = {
            "padding": "8px",
            "text-align": "left",
            "border": "1px solid #ddd"
        }

        # Create header row
        header_cells = [html.Th(header, style=header_style) for header in headers]
        header_row = html.Tr(header_cells)

        # Create data rows
        data_rows = []
        for i, row in enumerate(rows):
            # Alternate row colors for better readability
            row_style = {"background-color": "#f9f9f9"} if i % 2 == 0 else {}

            cells = [html.Td(cell, style={**cell_style, **row_style}) for cell in row]
            data_rows.append(html.Tr(cells))

        return html.Table([header_row] + data_rows, style=table_style)


class GuidellmPerformanceAnalysisReport():
    def __init__(self):
        self.name = "report: GuideLLM Performance Analysis"
        self.id_name = self.name.lower().replace(" ", "_").replace("-", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, *args):
        """
        Generate focused report showing token throughput and TTFT performance analysis
        """
        ordered_vars, settings, setting_lists, variables, cfg = args
        entries = list(common.Matrix.all_records(settings, setting_lists))

        header = []
        header.append(html.H2("📊 GuideLLM: Performance Analysis"))
        header.append(html.P("Comprehensive performance analysis including token throughput scaling and TTFT latency patterns across different test configurations"))
        header.append(html.Br())

        if not entries:
            header.append(html.P("No test entries found."))
            return None, header

        # Check if we have GuideLLM benchmark data
        has_guidellm_data = False
        for entry in entries:
            if hasattr(entry.results, 'guidellm_benchmarks') and entry.results.guidellm_benchmarks:
                has_guidellm_data = True
                break

        if not has_guidellm_data:
            header.append(html.P("⚠️ No GuideLLM benchmark data available."))
            header.append(html.P("This report requires GuideLLM benchmark results to analyze token throughput scaling."))
            header.append(html.P("To enable benchmarks, set tests.llmd.benchmarks.guidellm.enabled: true in the configuration."))
            return None, header

        # Token Throughput Analysis Section
        header.append(html.H3("🚀 Token Throughput vs Concurrency"))
        header.append(html.P("Analysis of how token generation throughput scales with concurrency levels"))
        header += report.Plot_and_Text("Guidellm Tokens vs Concurrency", args)

        # TTFT Analysis Section
        header.append(html.H3("⚡ Time to First Token (TTFT) Analysis"))
        header.append(html.P("Latency analysis showing response time percentiles across different concurrency levels"))
        header += report.Plot_and_Text("Guidellm TTFT Analysis", args)

        # TPOT Analysis Section
        header.append(html.H3("🔄 Time Per Output Token (TPOT) Analysis"))
        header.append(html.P("Token generation speed analysis showing how quickly individual tokens are produced"))
        header += report.Plot_and_Text("Guidellm TPOT Analysis", args)

        # ITL Analysis Section
        header.append(html.H3("⏱️ Inter-Token Latency (ITL) Analysis"))
        header.append(html.P("Streaming responsiveness analysis showing the delay between consecutive tokens"))
        header += report.Plot_and_Text("Guidellm ITL Analysis", args)

        # E2E Latency Analysis Section
        header.append(html.H3("🎯 End-to-End (E2E) Latency Analysis"))
        header.append(html.P("Complete request duration analysis from request initiation to final response completion"))
        header += report.Plot_and_Text("Guidellm E2E Latency Analysis", args)

        # Add summary analysis section
        header.append(html.H3("📈 Key Insights"))

        # Collect all GuideLLM benchmarks for analysis
        all_benchmarks = []
        benchmark_configs = []
        for entry in entries:
            if hasattr(entry.results, 'guidellm_benchmarks') and entry.results.guidellm_benchmarks:
                entry_name = entry.get_name(variables) if variables else f"Unknown Configuration"
                for benchmark in entry.results.guidellm_benchmarks:
                    if benchmark.strategy != "throughput":  # Skip throughput-only strategies
                        all_benchmarks.append(benchmark)
                        benchmark_configs.append(entry_name)

        if all_benchmarks:
            # Find best token throughput performers
            best_tokens_idx = max(range(len(all_benchmarks)), key=lambda i: all_benchmarks[i].tokens_per_second)
            best_efficiency_idx = max(range(len(all_benchmarks)), key=lambda i: all_benchmarks[i].tokens_per_second / max(all_benchmarks[i].request_concurrency, 1))

            best_tokens = all_benchmarks[best_tokens_idx]
            best_efficiency = all_benchmarks[best_efficiency_idx]

            # Configuration analysis
            configurations = {}
            for i, benchmark in enumerate(all_benchmarks):
                config = benchmark_configs[i]
                if config not in configurations:
                    configurations[config] = {
                        'max_tokens': 0,
                        'optimal_concurrency': 0,
                        'strategies': 0
                    }

                if benchmark.tokens_per_second > configurations[config]['max_tokens']:
                    configurations[config]['max_tokens'] = benchmark.tokens_per_second
                    configurations[config]['optimal_concurrency'] = benchmark.request_concurrency

                configurations[config]['strategies'] += 1

            # Sort configurations by performance
            sorted_configs = sorted(configurations.items(), key=lambda x: x[1]['max_tokens'], reverse=True)

            insights = [
                f"🏆 Best token throughput: {best_tokens.strategy} in {benchmark_configs[best_tokens_idx]} ({best_tokens.tokens_per_second:.0f} tok/s)",
                f"⚡ Most efficient: {best_efficiency.strategy} in {benchmark_configs[best_efficiency_idx]} ({(best_efficiency.tokens_per_second / max(best_efficiency.request_concurrency, 1)):.0f} tok/s per concurrency unit)",
                f"📊 Total configurations tested: {len(configurations)}",
                f"🎯 Total strategies analyzed: {len(all_benchmarks)}"
            ]

            for insight in insights:
                header.append(html.P(insight))

            if len(sorted_configs) > 1:
                header.append(html.Br())
                header.append(html.H4("🔧 Configuration Performance Ranking"))

                for i, (config, metrics) in enumerate(sorted_configs):
                    rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else "📍"
                    header.append(html.P(f"{rank_emoji} {config}: {metrics['max_tokens']:.0f} tok/s (optimal concurrency: {metrics['optimal_concurrency']:.0f}, {metrics['strategies']} strategies)"))

            header.append(html.Br())
            header.append(html.P("💡 Use this analysis to identify optimal concurrency settings for maximum token generation throughput in your specific deployment configuration."))

        else:
            header.append(html.P("No benchmark data available for analysis."))

        return None, header
