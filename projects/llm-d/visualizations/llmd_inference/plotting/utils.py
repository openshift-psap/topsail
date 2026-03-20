"""
Utility functions for LLM-D visualization plotting modules
"""

import logging
from dash import html
import matrix_benchmarking.common as common


def check_prometheus_data_availability(metric_type, report_name):
    """
    Check if Prometheus metrics data is available and return appropriate response

    Args:
        metric_type: Type of metrics to check ("sutest" for main Prometheus, "uwm" for User Workload Monitoring)
        report_name: Human-readable name of the report for logging

    Returns:
        tuple: (has_data: bool, error_elements: list)
               - has_data: True if metrics data is available
               - error_elements: HTML elements to display if no data (empty list if data available)
    """
    entries = list(common.Matrix.all_records(None, None))

    # Check if any entries have the requested metrics data
    has_metrics_data = False
    for entry in entries:
        try:
            if (hasattr(entry.results, 'metrics') and
                entry.results.metrics and
                entry.results.metrics.get(metric_type)):
                has_metrics_data = True
                break
        except Exception:
            continue

    if not has_metrics_data:
        logging.info(f"No {metric_type} Prometheus metrics data found - skipping {report_name} generation")

        # Generate appropriate error message based on metric type
        if metric_type == "uwm":
            error_elements = [
                html.P("⚠️ No Prometheus User Workload Monitoring metrics data available."),
                html.P("This report requires UWM metrics to be captured during the test run."),
                html.P("To enable metrics collection, set tests.capture_prom_uwm: true in the configuration.")
            ]
        else:  # sutest/main prometheus
            error_elements = [
                html.P("⚠️ No Prometheus cluster metrics data available."),
                html.P("This report requires cluster-level Prometheus metrics to be captured during the test run."),
                html.P("To enable metrics collection, set tests.capture_prom: true in the configuration.")
            ]

        return False, error_elements

    return True, []