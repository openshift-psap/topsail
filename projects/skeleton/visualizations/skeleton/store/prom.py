from collections import defaultdict
import json

from matrix_benchmarking import common
import matrix_benchmarking.plotting.prom as plotting_prom
import matrix_benchmarking.parsing.prom as parsing_prom
import matrix_benchmarking.plotting.prom.cpu_memory as plotting_prom_cpu_memory

import projects.core.visualizations.helpers.store.prom as core_prom_store


def get_sutest_metrics(register=False):
    cluster_role = "sutest"

    all_metrics = []
    all_metrics += core_prom_store.get_cluster_metrics(cluster_role, gpu=False, register=register)

    return all_metrics


def register(only_initialize=False):
    register = not only_initialize

    get_sutest_metrics(register)
