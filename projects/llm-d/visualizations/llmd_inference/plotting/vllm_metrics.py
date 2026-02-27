from dash import html

import projects.matrix_benchmarking.visualizations.helpers.plotting.prom as plotting_prom
import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common


def register():
    """Register all VLLM-specific Prometheus metrics as individual plots"""

    # Get metrics function for UWM data
    def get_uwm_metrics(entry, metric):
        try:
            return entry.results.metrics["uwm"][metric]
        except KeyError:
            return []

    # =========================================================================
    # 🚀 END-TO-END LATENCY METRICS
    # =========================================================================

    # E2E Request Latency - Average latency per request
    plotting_prom.Plot(
        ["vllm_e2e_latency_average"],
        "Prom: VLLM E2E Request Latency (Average)",
        title="VLLM End-to-End Request Latency (Average)",
        y_title="Latency (seconds)",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # E2E Request Rate - Requests per second
    plotting_prom.Plot(
        [{"vllm_e2e_request_rate": "rate(vllm_e2e_latency_seconds_count[5m])"}],
        "Prom: VLLM E2E Request Rate",
        title="VLLM End-to-End Request Rate",
        y_title="Requests/sec",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # =========================================================================
    # ⚡ TIME TO FIRST TOKEN (TTFT) METRICS
    # =========================================================================

    # TTFT Average latency
    plotting_prom.Plot(
        ["vllm_ttft_average"],
        "Prom: VLLM Time to First Token (Average)",
        title="VLLM Time to First Token (Average)",
        y_title="TTFT (seconds)",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # TTFT Request Rate
    plotting_prom.Plot(
        ["vllm_ttft_rate"],
        "Prom: VLLM TTFT Request Rate",
        title="VLLM TTFT Request Rate",
        y_title="Requests/sec",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # =========================================================================
    # 🔄 INTER-TOKEN LATENCY METRICS
    # =========================================================================

    # Inter-token Average latency
    plotting_prom.Plot(
        ["vllm_inter_token_average"],
        "Prom: VLLM Inter-Token Latency (Average)",
        title="VLLM Inter-Token Latency (Average)",
        y_title="Latency (seconds)",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # Inter-token Request Rate
    plotting_prom.Plot(
        ["vllm_inter_token_rate"],
        "Prom: VLLM Inter-Token Request Rate",
        title="VLLM Inter-Token Request Rate",
        y_title="Requests/sec",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # =========================================================================
    # 🔧 REQUEST PROCESSING PHASE METRICS
    # =========================================================================

    # Prefill Phase - Average time per request
    plotting_prom.Plot(
        ["vllm_prefill_average"],
        "Prom: VLLM Request Prefill Time (Average)",
        title="VLLM Request Prefill Time (Average)",
        y_title="Time (seconds)",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # Prefill Phase - Rate of time spent
    plotting_prom.Plot(
        ["vllm_prefill_rate"],
        "Prom: VLLM Request Prefill Time Rate",
        title="VLLM Request Prefill Time Rate",
        y_title="Seconds/sec",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # Decode Phase - Average time per request
    plotting_prom.Plot(
        ["vllm_decode_average"],
        "Prom: VLLM Request Decode Time (Average)",
        title="VLLM Request Decode Time (Average)",
        y_title="Time (seconds)",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # Decode Phase - Rate of time spent
    plotting_prom.Plot(
        ["vllm_decode_rate"],
        "Prom: VLLM Request Decode Time Rate",
        title="VLLM Request Decode Time Rate",
        y_title="Seconds/sec",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # Queue Time - Average time per request
    plotting_prom.Plot(
        ["vllm_queue_average"],
        "Prom: VLLM Request Queue Time (Average)",
        title="VLLM Request Queue Time (Average)",
        y_title="Time (seconds)",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # Queue Time - Rate of time spent
    plotting_prom.Plot(
        ["vllm_queue_rate"],
        "Prom: VLLM Request Queue Time Rate",
        title="VLLM Request Queue Time Rate",
        y_title="Seconds/sec",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # =========================================================================
    # 🔤 TOKEN THROUGHPUT METRICS
    # =========================================================================

    # Token throughput rates
    plotting_prom.Plot(
        ["vllm_prompt_tokens_rate"],
        "Prom: VLLM Prompt Tokens Rate",
        title="VLLM Prompt Tokens Rate",
        y_title="Tokens/sec",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    plotting_prom.Plot(
        ["vllm_generation_tokens_rate"],
        "Prom: VLLM Generation Tokens Rate",
        title="VLLM Generation Tokens Rate",
        y_title="Tokens/sec",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # Combined token throughput
    plotting_prom.Plot(
        ["vllm_total_tokens_rate"],
        "Prom: VLLM Total Tokens Rate",
        title="VLLM Total Tokens Rate (Prompt + Generation)",
        y_title="Tokens/sec",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # Average max generation tokens per request
    plotting_prom.Plot(
        ["vllm_avg_max_gen_tokens"],
        "Prom: VLLM Avg Max Generation Tokens",
        title="VLLM Average Max Generation Tokens per Request",
        y_title="Tokens",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # =========================================================================
    # 📊 REQUEST QUEUE STATE AND CAPACITY
    # =========================================================================

    # Current queue state (gauge metrics - no transformation needed)
    plotting_prom.Plot(
        ["vllm_num_requests_running"],
        "Prom: VLLM Running Requests",
        title="VLLM Number of Running Requests",
        y_title="Request Count",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    plotting_prom.Plot(
        ["vllm_num_requests_waiting"],
        "Prom: VLLM Waiting Requests",
        title="VLLM Number of Waiting Requests",
        y_title="Request Count",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    plotting_prom.Plot(
        ["vllm_kv_cache_usage_perc"],
        "Prom: VLLM KV Cache Usage",
        title="VLLM KV Cache Usage Percentage",
        y_title="Usage (%)",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # Request success rate
    plotting_prom.Plot(
        ["vllm_request_success_rate"],
        "Prom: VLLM Request Success Rate",
        title="VLLM Request Success Rate",
        y_title="Successful Requests/sec",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )

    # Request success increase (over time window)
    plotting_prom.Plot(
        ["vllm_request_success_increase"],
        "Prom: VLLM Request Success Increase",
        title="VLLM Request Success (5m increase)",
        y_title="Successful Requests",
        get_metrics=get_uwm_metrics,
        as_timestamp=True
    )


class VLLMMetricsReport():
    def __init__(self):
        self.name = "report: VLLM Metrics Analysis"
        self.id_name = self.name.lower().replace(" ", "_").replace("-", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, *args):
        """
        Generate comprehensive VLLM metrics analysis report
        """
        ordered_vars, settings, setting_lists, variables, cfg = args
        entries = list(common.Matrix.all_records(settings, setting_lists))

        header = []
        header.append(html.H2("🔥 VLLM Performance Metrics Analysis"))
        header.append(html.P("Comprehensive analysis of VLLM inference server metrics from User Workload Monitoring"))
        header.append(html.Br())

        if not entries:
            header.append(html.P("No test entries found."))
            return None, header

        # End-to-End Latency Section
        header.append(html.H3("🚀 End-to-End Request Latency"))
        header.append(html.P("Overall request processing time and throughput from client perspective"))

        header += report.Plot_and_Text("Prom: VLLM E2E Request Latency (Average)", args)
        header += report.Plot_and_Text("Prom: VLLM E2E Request Rate", args)

        header.append(html.Br())

        # Time to First Token Section
        header.append(html.H3("⚡ Time to First Token (TTFT)"))
        header.append(html.P("Critical metric for perceived responsiveness - time until first token is generated"))

        header += report.Plot_and_Text("Prom: VLLM Time to First Token (Average)", args)
        header += report.Plot_and_Text("Prom: VLLM TTFT Request Rate", args)

        header.append(html.Br())

        # Inter-Token Latency Section
        header.append(html.H3("🔄 Inter-Token Latency"))
        header.append(html.P("Streaming quality - time between generated tokens"))

        header += report.Plot_and_Text("Prom: VLLM Inter-Token Latency (Average)", args)
        header += report.Plot_and_Text("Prom: VLLM Inter-Token Request Rate", args)

        header.append(html.Br())

        # Request Processing Phases Section
        header.append(html.H3("🔧 Request Processing Phases"))
        header.append(html.P("Detailed breakdown of request processing: prefill, decode, and queue times"))

        header.append(html.H4("Prefill Phase"))
        header += report.Plot_and_Text("Prom: VLLM Request Prefill Time (Average)", args)
        header += report.Plot_and_Text("Prom: VLLM Request Prefill Time Rate", args)

        header.append(html.H4("Decode Phase"))
        header += report.Plot_and_Text("Prom: VLLM Request Decode Time (Average)", args)
        header += report.Plot_and_Text("Prom: VLLM Request Decode Time Rate", args)

        header.append(html.H4("Queue Time"))
        header += report.Plot_and_Text("Prom: VLLM Request Queue Time (Average)", args)
        header += report.Plot_and_Text("Prom: VLLM Request Queue Time Rate", args)

        header.append(html.Br())

        # Token Throughput Section
        header.append(html.H3("🔤 Token Throughput"))
        header.append(html.P("Token generation rates and processing statistics"))

        header += report.Plot_and_Text("Prom: VLLM Prompt Tokens Rate", args)
        header += report.Plot_and_Text("Prom: VLLM Generation Tokens Rate", args)
        header += report.Plot_and_Text("Prom: VLLM Total Tokens Rate", args)
        header += report.Plot_and_Text("Prom: VLLM Avg Max Generation Tokens", args)

        header.append(html.Br())

        # Request Queue State Section
        header.append(html.H3("📊 Request Queue State & Success Metrics"))
        header.append(html.P("Server capacity utilization, queue state, and success rates"))

        header += report.Plot_and_Text("Prom: VLLM Running Requests", args)
        header += report.Plot_and_Text("Prom: VLLM Waiting Requests", args)
        header += report.Plot_and_Text("Prom: VLLM KV Cache Usage", args)
        header += report.Plot_and_Text("Prom: VLLM Request Success Rate", args)
        header += report.Plot_and_Text("Prom: VLLM Request Success Increase", args)

        return None, header


def register_report():
    """Register the VLLM metrics report"""
    VLLMMetricsReport()
