import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common
from dash import html

def register():
    LlmdInferenceErrorReport()

class LlmdInferenceErrorReport():
    def __init__(self):
        self.name = "report: LLM-D Inference Error Report"
        self.id_name = self.name.lower().replace(" ", "_").replace("-", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, *args):
        """
        Generate error analysis report showing what has been tested
        """
        ordered_vars, settings, setting_lists, variables, cfg = args
        entries = list(common.Matrix.all_records(settings, setting_lists))

        header = []
        header.append(html.H2("LLM-D Inference Test Analysis"))
        header.append(html.Br())

        if not entries:
            header.append(html.P("No test entries found."))
            return None, header

        # Count successful vs failed tests
        total_tests = len(entries)
        successful_tests = 0
        failed_tests = 0
        guidellm_available = 0
        multiturn_available = 0
        prometheus_available = 0

        for entry in entries:
            results = entry.results

            # Count test outcomes
            if hasattr(results, 'test_success') and results.test_success:
                successful_tests += 1
            else:
                failed_tests += 1

            # Count available data sources
            if hasattr(results, 'guidellm_benchmarks') and results.guidellm_benchmarks:
                guidellm_available += 1

            if hasattr(results, 'multiturn_benchmark') and results.multiturn_benchmark:
                multiturn_available += 1

            if hasattr(results, 'prometheus_path') and results.prometheus_path:
                prometheus_available += 1

        # Overall test summary
        header.append(html.H3("Test Summary"))
        header.append(html.P(f"Total tests executed: {total_tests}"))

        if successful_tests > 0:
            header.append(html.P([
                "✅ Successful tests: ",
                html.Span(str(successful_tests), style={"color": "green", "font-weight": "bold"}),
                f" ({successful_tests/total_tests*100:.1f}%)"
            ]))

        if failed_tests > 0:
            header.append(html.P([
                "❌ Failed tests: ",
                html.Span(str(failed_tests), style={"color": "red", "font-weight": "bold"}),
                f" ({failed_tests/total_tests*100:.1f}%)"
            ]))

        header.append(html.Br())

        # Data availability summary
        header.append(html.H3("Data Sources Available"))
        header.append(html.Ul([
            html.Li([
                "🎯 GuideLLM benchmarks: ",
                html.Span(f"{guidellm_available}/{total_tests}", style={"font-weight": "bold"}),
                f" ({guidellm_available/total_tests*100:.1f}%)"
            ]),
            html.Li([
                "🔄 Multi-turn benchmarks: ",
                html.Span(f"{multiturn_available}/{total_tests}", style={"font-weight": "bold"}),
                f" ({multiturn_available/total_tests*100:.1f}%)"
            ]),
            html.Li([
                "📊 Prometheus monitoring: ",
                html.Span(f"{prometheus_available}/{total_tests}", style={"font-weight": "bold"}),
                f" ({prometheus_available/total_tests*100:.1f}%)"
            ])
        ]))

        header.append(html.Br())

        # Detailed test breakdown
        header.append(html.H3("Individual Test Details"))

        for i, entry in enumerate(entries):
            results = entry.results
            test_status = "✅ PASSED" if (hasattr(results, 'test_success') and results.test_success) else "❌ FAILED"

            header.append(html.H4(f"Test {i+1}: {test_status}"))

            # Test metadata if available
            if hasattr(results, 'test_name'):
                header.append(html.P(f"Test name: {results.test_name}"))

            if hasattr(results, 'test_failure_reason') and results.test_failure_reason:
                header.append(html.P([
                    "Failure reason: ",
                    html.Span(results.test_failure_reason, style={"color": "red", "font-style": "italic"})
                ]))

            # Get artifacts base directory for links
            artifacts_basedir = getattr(results, 'from_local_env', {})
            if hasattr(artifacts_basedir, 'artifacts_basedir'):
                artifacts_basedir = artifacts_basedir.artifacts_basedir
            else:
                artifacts_basedir = None

            # Create links to key artifacts
            artifact_links = []

            if artifacts_basedir:
                # Main test artifacts directory
                artifact_links.append(html.Li([
                    html.A("🗂️ Test artifacts directory", href=str(artifacts_basedir), target="_blank")
                ]))

                # LLM Inference Service deployment logs
                llm_deployment_dir = artifacts_basedir / "001__deploy_llm_inference_service"
                if llm_deployment_dir.exists():
                    artifact_links.append(html.Li([
                        html.A("🚀 LLM Inference Service deployment", href=str(llm_deployment_dir), target="_blank")
                    ]))

                # GuideLLM benchmark results
                if hasattr(results, 'guidellm_benchmarks') and results.guidellm_benchmarks:
                    strategy_count = len(results.guidellm_benchmarks)

                    # Look for guidellm benchmark directory
                    guidellm_dir = None
                    for item in artifacts_basedir.iterdir():
                        if item.is_dir() and 'guidellm_benchmark' in item.name:
                            guidellm_dir = item
                            break

                    if guidellm_dir:
                        artifact_links.append(html.Li([
                            html.A(f"📊 GuideLLM benchmark results ({strategy_count} strategies)",
                                  href=str(guidellm_dir), target="_blank")
                        ]))

                        # Link to specific log file if it exists
                        log_file = guidellm_dir / "000__llmd__run_guidellm_benchmark" / "artifacts" / "guidellm_benchmark_job.logs"
                        if log_file.exists():
                            artifact_links.append(html.Li([
                                "  └─ ", html.A("benchmark logs", href=str(log_file), target="_blank")
                            ]))

                # Multi-turn benchmark results
                if hasattr(results, 'multiturn_benchmark') and results.multiturn_benchmark:
                    # Look for multiturn benchmark directory
                    multiturn_dir = None
                    for item in artifacts_basedir.iterdir():
                        if item.is_dir() and 'multiturn_benchmark' in item.name:
                            multiturn_dir = item
                            break

                    if multiturn_dir:
                        artifact_links.append(html.Li([
                            html.A("🔄 Multi-turn benchmark results",
                                  href=str(multiturn_dir), target="_blank")
                        ]))

                        # Link to specific log file if it exists
                        log_file = multiturn_dir / "000__llmd__run_multiturn_benchmark" / "artifacts" / "multiturn_benchmark_job.logs"
                        if log_file.exists():
                            artifact_links.append(html.Li([
                                "  └─ ", html.A("benchmark logs", href=str(log_file), target="_blank")
                            ]))

                # Prometheus monitoring data
                if hasattr(results, 'prometheus_path') and results.prometheus_path:
                    # Look for prometheus dump directory
                    prom_dir = None
                    for item in artifacts_basedir.iterdir():
                        if item.is_dir() and 'prometheus_db' in item.name:
                            prom_dir = item
                            break

                    if prom_dir:
                        artifact_links.append(html.Li([
                            html.A("📈 Prometheus monitoring data",
                                  href=str(prom_dir), target="_blank")
                        ]))

            # Show artifact links if available
            if artifact_links:
                header.append(html.P("🔗 Artifact links:"))
                header.append(html.Ul(artifact_links))
            else:
                header.append(html.P("🔗 Artifact links: Not available"))

            # Data sources status summary
            data_sources = []
            if hasattr(results, 'guidellm_benchmarks') and results.guidellm_benchmarks:
                strategy_count = len(results.guidellm_benchmarks)
                data_sources.append(f"✅ GuideLLM ({strategy_count} strategies)")
            else:
                data_sources.append("❌ GuideLLM")

            if hasattr(results, 'multiturn_benchmark') and results.multiturn_benchmark:
                data_sources.append("✅ Multi-turn")
            else:
                data_sources.append("❌ Multi-turn")

            if hasattr(results, 'prometheus_path') and results.prometheus_path:
                data_sources.append("✅ Prometheus")
            else:
                data_sources.append("❌ Prometheus")

            header.append(html.P("Data sources: " + " | ".join(data_sources)))
            header.append(html.Br())

        return None, header
