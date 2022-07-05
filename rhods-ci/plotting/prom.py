from collections import defaultdict

import matrix_benchmarking.plotting.prom as plotting_prom
import matrix_benchmarking.parsing.prom as parsing_prom

def _get_container_cpu(**kwargs):
    #if "container" in kwargs: del kwargs["container"]
    container_labels = ",".join(f"{k}=~'{v}'" for k, v in kwargs.items())

    return [
        "pod:container_cpu_usage:sum{"+container_labels+"}",
        "kube_pod_container_resource_requests{"+container_labels+",resource='cpu'}",
        "kube_pod_container_resource_limits{"+container_labels+",resource='cpu'}",
    ]

def _get_container_mem(**kwargs):
    container_labels = ",".join(f"{k}=~'{v}'" for k, v in kwargs.items())

    return [
        "container_memory_rss{"+container_labels+"}",
        "kube_pod_container_resource_requests{"+container_labels+",resource='memory'}",
        "kube_pod_container_resource_limits{"+container_labels+",resource='memory'}",
    ]

def _get_container_cpu_mem(**kwargs):
    return _get_container_mem(**kwargs) + _get_container_mem(**kwargs)

def _get_cluster_mem():
    return ["cluster:capacity_memory_bytes:sum{label_node_role_kubernetes_io !~ 'master'}"]

def _get_cluster_cpu():
    return ["cluster:capacity_cpu_cores:sum{label_node_role_kubernetes_io !~ 'master'}"]

# ---

def _get_cluster_mem_cpu(cluster_role, register):
    all_metrics = []

    cluster_mem = _get_cluster_mem()
    cluster_cpu = _get_cluster_cpu()

    all_metrics += cluster_mem
    all_metrics += cluster_cpu

    if register:
        plotting_prom.Plot(cluster_mem, f"{cluster_role} cluster memory capacity",
                           get_metrics=get_metrics(cluster_role),
                           as_timestamp=True)

        plotting_prom.Plot(cluster_cpu, f"{cluster_role} cluster CPU capacity",
                           get_metrics=get_metrics(cluster_role),
                           as_timestamp=True)

    return all_metrics


def _get_container_mem_cpu(cluster_role, register, container_label_sets):
    all_metrics = []

    for labels in container_label_sets:
        mem = _get_container_mem(**labels)
        cpu = _get_container_cpu(**labels)

        all_metrics += mem
        all_metrics += cpu

        if not register: continue
        name = ", ".join([f"{k}={v}" for k, v in labels.items()])

        plotting_prom.Plot(cpu, f"CPU usage {name}",
                           get_metrics=get_metrics(cluster_role),
                           as_timestamp=True)
        plotting_prom.Plot(mem, f"memory usage {name}",
                           get_metrics=get_metrics(cluster_role),
                           as_timestamp=True)

    return all_metrics

def _get_authentication(cluster_role, register):
    metric_groups = [
        ["openshift_auth_basic_password_count", "openshift_auth_basic_password_count_result",],
        ["openshift_auth_form_password_count", "openshift_auth_form_password_count_result",],
        ["openshift_auth_password_total"],
    ]

    if register:
        for metrics in metric_groups:
                    plotting_prom.Plot(metrics, f"OAuth {' '.join(metrics)}",
                           get_metrics=get_metrics(cluster_role),
                           as_timestamp=True)
    all_metrics = []
    for metrics in metric_groups:
        all_metrics += metrics

    return all_metrics
# ---

def get_sutest_metrics(register=False):
    cluster_role = "sutest"

    container_labels = [
        dict(namespace="rhods-notebooks"),
        dict(namespace="openldap",pod="openldap.*"),
        dict(namespace="redhat-ods-applications",pod="rhods-dashboard.*"),
        dict(namespace="openshift-authentication",pod="oauth-openshift.*"),
    ]
    all_metrics = []
    all_metrics += _get_cluster_mem_cpu(cluster_role, register)
    all_metrics += _get_container_mem_cpu(cluster_role, register, container_labels)
    all_metrics += _get_authentication(cluster_role, register)

    return all_metrics


def get_driver_metrics(register=False):
    cluster_role = "driver"

    container_labels = [
        dict(namespace="loadtest"),
    ]
    all_metrics = []
    all_metrics += _get_cluster_mem_cpu(cluster_role, register)
    all_metrics += _get_container_mem_cpu(cluster_role, register, container_labels)

    return all_metrics


def get_rhods_metrics(register=False):
    return []

# ---

def get_metrics(name):
    def _get_metrics(entry, metric):
        try:
            return entry.results.metrics[name][metric]
        except KeyError:
            return []
    return _get_metrics


def register():
    get_sutest_metrics(register=True)
    get_driver_metrics(register=True)
    get_rhods_metrics(register=True)
