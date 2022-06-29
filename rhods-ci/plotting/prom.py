from collections import defaultdict

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

from . import simple_timeline
from . import advanced_timeline
import matrix_benchmarking.plotting.prom as plotting_prom
import matrix_benchmarking.parsing.prom as parsing_prom

def filter_driver_metrics(metrics):
    found_it = False
    for metric in parsing_prom.filter_value_in_label(metrics, "loadtest", "namespace"):
        yield metric


def filter_sutest_metrics(metrics):
    found_it = False
    for metric in parsing_prom.filter_value_in_label(metrics, "rhods-notebooks", "namespace"):
        yield metric


def get_metrics(name):
    def _get_metrics(entry, metric):
        try:
            return entry.results.metrics[name][metric]
        except KeyError:
            return []
    return _get_metrics


def register():
    plotting_prom.Plot("pod:container_cpu_usage:sum", "Test Pod CPU usage",
                       get_metrics=get_metrics("driver"),
                       filter_metrics=filter_driver_metrics,
                       as_timestamp=True)

    plotting_prom.Plot("pod:container_cpu_usage:sum", "Notebook Pod CPU usage",
                       get_metrics=get_metrics("sutest"),
                       filter_metrics=filter_sutest_metrics,
                       as_timestamp=True)

    plotting_prom.Plot("container_memory_rss", "Test Pod memory usage",
                       get_metrics=get_metrics("driver"),
                       filter_metrics=filter_driver_metrics,
                       as_timestamp=True)
