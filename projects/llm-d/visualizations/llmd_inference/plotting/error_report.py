import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common
from dash import html
import yaml
import pathlib

def analyze_llmisvc_deployment(llmisvc_config):
    """
    Analyze LLMISVC deployment configuration

    Args:
        llmisvc_config: Parsed LLMISVC configuration dict

    Returns formatted HTML content showing deployment details
    """
    if not llmisvc_config:
        return [html.P("❌ No LLMISVC configuration available")]

    isvc_data = llmisvc_config

    def safe_get(data, path, default="missing"):
        """Safely navigate nested dict path"""
        try:
            current = data
            for key in path.split('.'):
                if '[' in key and ']' in key:
                    # Handle array access like containers[0]
                    array_key, index = key.split('[')
                    index = int(index.rstrip(']'))
                    current = current[array_key][index]
                else:
                    current = current[key]
            return current
        except (KeyError, IndexError, TypeError):
            return default

    def get_vllm_args(containers_section):
        """Extract VLLM_ADDITIONAL_ARGS from containers section"""
        if containers_section == "missing":
            return "missing"
        try:
            for container in containers_section:
                if container.get('name') == 'main':
                    env_vars = container.get('env', [])
                    for env_var in env_vars:
                        if env_var.get('name') == 'VLLM_ADDITIONAL_ARGS':
                            return env_var.get('value', 'empty')
            return "not set"
        except (TypeError, KeyError):
            return "missing"

    def get_epp_config(router_args):
        """Extract EPP config from router scheduler args"""
        if router_args == "missing":
            return "missing"
        try:
            if isinstance(router_args, list) and len(router_args) > 0:
                # Find --config-text and get the next argument
                for i, arg in enumerate(router_args):
                    if arg == '--config-text' and i + 1 < len(router_args):
                        return router_args[i + 1]
            return "not set"
        except (TypeError, IndexError):
            return "missing"

    def format_resources(resources):
        """Format resource requirements for display"""
        if resources == "missing":
            return "missing"
        try:
            return "\n" + yaml.dump(dict(resources=resources)).replace("resources:\n", "")
        except (TypeError, AttributeError):
            return "invalid format"

    # Build analysis content
    analysis_content = []

    # Model spec
    model_uri = safe_get(isvc_data, 'spec.model.uri')
    model_name = safe_get(isvc_data, 'spec.model.name')

    # Main template
    main_replicas = safe_get(isvc_data, 'spec.replicas')
    main_containers = safe_get(isvc_data, 'spec.template.containers')
    main_vllm_args = get_vllm_args(main_containers)
    main_resources = safe_get(isvc_data, 'spec.template.containers[0].resources')

    # Router/EPP
    router_args = safe_get(isvc_data, 'spec.router.scheduler.template.containers[0].args')
    epp_config = get_epp_config(router_args)

    # Prefill (if exists)
    prefill_replicas = safe_get(isvc_data, 'spec.prefill.replicas')
    prefill_containers = safe_get(isvc_data, 'spec.prefill.template.containers') if prefill_replicas != "missing" else "missing"
    prefill_vllm_args = get_vllm_args(prefill_containers) if prefill_replicas != "missing" else "missing"
    prefill_resources = safe_get(isvc_data, 'spec.prefill.template.containers[0].resources') if prefill_replicas != "missing" else "missing"

    # Code block styling
    code_style = {
        "background-color": "#f8f8f8",
        "padding": "10px",
        "border-radius": "5px",
        "font-family": "monospace",
        "font-size": "0.9em",
        "white-space": "pre-wrap",
        "overflow": "auto",
        "margin": "10px 0"
    }

    # Model specification section
    analysis_content.append(html.H6("=== MODEL SPECIFICATION ==="))
    model_lines = [
        f"name: {model_name}",
        f"uri: {model_uri}",
    ]
    analysis_content.append(html.Pre("\n".join(model_lines), style=code_style))

    # Main template section
    analysis_content.append(html.H6("=== MAIN TEMPLATE ==="))
    main_lines = [
        f"replicas: {main_replicas}", "",
        f"VLLM_ADDITIONAL_ARGS: \n- " + f"\n- ".join(main_vllm_args.split()), "",
        f"resources: {format_resources(main_resources)}"
    ]
    analysis_content.append(html.Pre("\n".join(main_lines), style=code_style))

    # Router/EPP configuration section
    analysis_content.append(html.H6("=== ROUTER/EPP CONFIGURATION ==="))
    if epp_config not in ["missing", "not set"]:
        epp_lines = [
            epp_config
        ]
    else:
        epp_lines = [f"EPP Config: {epp_config}"]
    analysis_content.append(html.Pre("\n".join(epp_lines), style=code_style))

    # Prefill template section
    analysis_content.append(html.H6("=== PREFILL TEMPLATE ==="))
    if prefill_replicas != "missing":
        prefill_lines = [
            f"replicas: {prefill_replicas}", "",
            f"VLLM_ADDITIONAL_ARGS: \n-" + "\n- ".join(prefill_vllm_args.split()), "",
            f"resources: {format_resources(prefill_resources)}"
        ]
    else:
        prefill_lines = ["not configured"]

    analysis_content.append(html.Pre("\n".join(prefill_lines), style=code_style))

    return analysis_content


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
        prometheus_available = 0
        llmisvc_available = 0

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

            if hasattr(results, 'metrics') and results.metrics:
                prometheus_available += 1

            if hasattr(results, 'llmisvc_config') and results.llmisvc_config:
                llmisvc_available += 1

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
                "📊 Prometheus monitoring: ",
                html.Span(f"{prometheus_available}/{total_tests}", style={"font-weight": "bold"}),
                f" ({prometheus_available/total_tests*100:.1f}%)"
            ]),
            html.Li([
                "🚀 LLMISVC configuration: ",
                html.Span(f"{llmisvc_available}/{total_tests}", style={"font-weight": "bold"}),
                f" ({llmisvc_available/total_tests*100:.1f}%)"
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

            # Show test entry labels
            labels_list = []

            for key, value in entry.settings.__dict__.items():
                labels_list.append(html.Code(f"{key}={value}", style={
                    "background-color": "#f8f8f8",
                    "padding": "2px 4px",
                    "margin": "2px",
                    "border-radius": "3px",
                    "font-size": "0.9em"
                }))
                labels_list.append(" ")

            header.append(html.P([
                "Settings: ",
                html.Span(labels_list)
            ]))

            header.append(html.P([
                "Directory: ",
                html.Code(str(entry.location).strip("./"), style={
                    "background-color": "#f8f8f8",
                    "padding": "2px 4px",
                    "border-radius": "3px",
                    "font-size": "0.9em"
                })
            ]))

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

                # Prometheus monitoring data
                if hasattr(results, 'metrics') and results.metrics:
                    # Look for prometheus dump directory
                    for prom_name in results.metrics:
                        if results.metrics[prom_name]:
                            artifact_links.append(html.Li([
                                f"📈 Prometheus '{prom_name}' monitoring data",
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

            if hasattr(results, 'metrics') and results.metrics:
                data_sources.append("✅ Prometheus")
            else:
                data_sources.append("❌ Prometheus")

            header.append(html.P("Data sources: " + " | ".join(data_sources)))

            # LLMISVC deployment analysis
            header.append(html.H5("LLMISVC Deployment Configuration"))
            llmisvc_analysis = analyze_llmisvc_deployment(results.llmisvc_config)
            header.extend(llmisvc_analysis)

            header.append(html.Br())

        return None, header
