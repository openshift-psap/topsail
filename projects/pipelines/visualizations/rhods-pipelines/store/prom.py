import logging

import projects.matrix_benchmarking.visualizations.helpers.store.prom as helper_prom_store
import matrix_benchmarking.plotting.prom.cpu_memory as plotting_prom_cpu_memory

SUTEST_CONTAINER_LABELS = [
    {"ODH DSP Operator": dict(namespace="redhat-ods-applications", pod="data-science-pipelines-operator-controller-manager.*")},
    {"KF Notebook Controller": dict(namespace="redhat-ods-applications", pod="notebook-controller-deployment.*")},
    {"ODH Notebook Controller": dict(namespace="redhat-ods-applications", pod="odh-notebook-controller-manager.*")},
]


def get_sutest_metrics(register=False):
    cluster_role = "sutest"

    all_metrics = []
    all_metrics += helper_prom_store.get_cluster_metrics(cluster_role, register=register, container_labels=SUTEST_CONTAINER_LABELS)

    return all_metrics


DRIVER_CONTAINER_LABELS = [
    {"Test Pods": dict(namespace="pipelines-scale-test.*", container="main")},
]


def get_driver_metrics(register=False):
    cluster_role = "driver"

    all_metrics = []
    all_metrics += helper_prom_store.get_cluster_metrics(cluster_role, register=register, container_labels=DRIVER_CONTAINER_LABELS)

    return all_metrics

DSPA_CONTAINER_LABELS = [
    {"DSPA Pods": dict(namespace="pipelines-test-.*", pod="(ds-pipeline-.*)|(mariadb-.*)|(minio-.*)")},
]

def get_dspa_metrics(register=False):
    cluster_role = "dspa"

    all_metrics = []
    all_metrics += helper_prom_store.get_cluster_metrics(cluster_role, register=register, container_labels=DSPA_CONTAINER_LABELS)

    return all_metrics

def register(only_initialize=False):
    register = not only_initialize

    get_dspa_metrics(register)
    get_sutest_metrics(register)
    get_driver_metrics(register)
