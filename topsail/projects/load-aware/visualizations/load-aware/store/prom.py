from collections import defaultdict
import json

from matrix_benchmarking import common
import matrix_benchmarking.plotting.prom as plotting_prom
import matrix_benchmarking.parsing.prom as parsing_prom
import matrix_benchmarking.plotting.prom.cpu_memory as plotting_prom_cpu_memory

from ..store import lts

def _labels_to_string(labels, exclude=[]):
    values = []
    for k, vals in labels.items():
        if k in exclude: continue

        if not isinstance(vals, list):
           vals = [vals]

        for v in vals:
            if v.startswith("!~"):
                op = "!~"
                v = v.replace("!~", "")
            else:
                op = "=~"

            values.append(f"{k}{op}'{v}'")

    return ",".join(values)

def _get_container_cpu(cluster_role, labels):
    labels_str = _labels_to_string(labels)

    metric_name = "_".join(f"{k}={v}" for k, v in labels.items())

    return [
        {f"{cluster_role}__container_cpu__{metric_name}": "rate(container_cpu_usage_seconds_total{"+labels_str+"}[5m])"},
        {f"{cluster_role}__container_sum_cpu__{metric_name}": "sum(rate(container_cpu_usage_seconds_total{"+labels_str+"}[5m]))"},
        {f"{cluster_role}__container_cpu_requests__{metric_name}": "kube_pod_container_resource_requests{"+labels_str+",resource='cpu'}"},
        {f"{cluster_role}__container_cpu_limits__{metric_name}": "kube_pod_container_resource_limits{"+labels_str+",resource='cpu'}"},
    ]

def _get_container_mem(cluster_role, labels):
    labels_str = _labels_to_string(labels)

    metric_name = "_".join(f"{k}={v}" for k, v in labels.items())

    return [
        {f"{cluster_role}__container_memory__{metric_name}": "container_memory_rss{"+labels_str+"}"},
        {f"{cluster_role}__container_memory_requests__{metric_name}": "kube_pod_container_resource_requests{"+labels_str+",resource='memory'}"},
        {f"{cluster_role}__container_memory_limits__{metric_name}": "kube_pod_container_resource_limits{"+labels_str+",resource='memory'}"},
    ]

def _get_container_cpu_mem(labelss):
    return _get_container_mem(labels) + _get_container_mem(labels)

def _get_cluster_mem(cluster_role):
    return [
        {f"{cluster_role}__cluster_memory_capacity": "sum(cluster:capacity_memory_bytes:sum)"},
        {f"{cluster_role}__cluster_memory_usage":
"""   sum(
        (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes)
        *
        on(instance) group_left(role) (
          label_replace(max by (node) (kube_node_role{role=~".+"}), "instance", "$1", "node", "(.*)")
        )
      )
"""},
        {f"{cluster_role}__cluster_memory_requests":
"""   sum(
        kube_pod_resource_request{resource="memory"}
        *
        on(node) group_left(role) (
          max by (node) (kube_node_role{role=~".+"})
        )
      )
"""},
    ]

def _get_cluster_cpu(cluster_role):
    return [
        {f"{cluster_role}__cluster_cpu_requests":
"""   sum(
        kube_pod_resource_request{resource="cpu"}
        *
        on(node) group_left(role) (
          max by (node) (kube_node_role{role=~".+"})
        )
      )
"""},

        {f"{cluster_role}__cluster_cpu_usage":
"""   sum(
        (
          1 - rate(node_cpu_seconds_total{mode="idle"}[2m])
          *
          on(namespace, pod) group_left(node) node_namespace_pod:kube_pod_info:{pod=~"node-exporter.+"}
        )
        *
        on(node) group_left(role) (
          max by (node) (kube_node_role{role=~".+"})
        )
      )
"""},
        {f"{cluster_role}__cluster_cpu_capacity": "sum(cluster:capacity_cpu_cores:sum)"}
    ]

# ---

def _get_cluster_mem_cpu(cluster_role, register):
    all_metrics = []

    cluster_mem = _get_cluster_mem(cluster_role)
    cluster_cpu = _get_cluster_cpu(cluster_role)

    all_metrics += cluster_mem
    all_metrics += cluster_cpu

    if register:
        plotting_prom_cpu_memory.Plot(cluster_mem, f"{cluster_role} cluster memory usage",
                                      get_metrics=get_metrics(cluster_role),
                                      as_timestamp=True,
                                      is_cluster=True,
                                      is_memory=True,
                                      )

        plotting_prom_cpu_memory.Plot(cluster_cpu, f"{cluster_role} cluster CPU usage",
                                      get_metrics=get_metrics(cluster_role),
                                      as_timestamp=True,
                                      is_cluster=True,
                                      )

    return all_metrics


def _get_container_mem_cpu(cluster_role, register, label_sets):
    all_metrics = []

    for plot_name_labels in label_sets:
        plot_name, labels = list(plot_name_labels.items())[0]

        mem = _get_container_mem(cluster_role, labels)
        cpu = _get_container_cpu(cluster_role, labels)

        all_metrics += mem
        all_metrics += cpu

        if not register: continue

        if cluster_role == 'sutest':
            for metric in cpu:
                for key in metric.keys():
                    if 'container=rhods-dashboard' in key:
                        lts.register_lts_metric(cluster_role, metric)

        container = labels.get("container", "all")

        plotting_prom_cpu_memory.Plot(cpu, f"{plot_name}: CPU usage",
                                      get_metrics=get_metrics(cluster_role),
                                      as_timestamp=True, container_name=container,
                                      )
        plotting_prom_cpu_memory.Plot(mem, f"{plot_name}: Mem usage",
                                      get_metrics=get_metrics(cluster_role),
                                      as_timestamp=True, is_memory=True,
                                      )

    return all_metrics


def _get_control_plane_nodes_cpu_usage(cluster_role, register):
    all_metrics = [
        {f"{cluster_role.title()} Control Plane Node CPU usage" : 'sum(irate(node_cpu_seconds_total[2m])) by (mode, instance) '},
        {f"{cluster_role.title()} Control Plane Node CPU idle" : 'sum(irate(node_cpu_seconds_total{mode="idle"}[2m])) by (mode, instance) '},
    ]

    def get_legend_name(metric_name, metric_metric):
        name = metric_metric['mode'] + " | " + metric_metric['instance'].split(".")[0]
        group = metric_metric['instance'].split(".")[0]
        return name, group

    def only_control_plane_nodes(entry, metrics):

        control_plane_nodes = [node.name for node in entry.results.cluster_info.control_plane]

        for metric in metrics:
            if metric.metric["instance"] not in control_plane_nodes:
                continue
            yield metric

    def no_control_plane_nodes(entry, metrics):
        control_plane_nodes = [node.name for node in entry.results.cluster_info.control_plane]

        for metric in metrics:
            if metric.metric["instance"] in control_plane_nodes:
                continue
            yield metric

    if register:
        for metric in all_metrics:
            name, rq = list(metric.items())[0]

            if 'CPU idle' in name and cluster_role == 'sutest':
                lts.register_lts_metric(cluster_role, metric)

            plotting_prom.Plot({name: rq},
                               f"Prom: {name}",
                               None,
                               "Count",
                               get_metrics=get_metrics(cluster_role),
                               filter_metrics=only_control_plane_nodes,
                               get_legend_name=get_legend_name,
                               show_queries_in_title=True,
                               show_legend=True,
                               higher_better=True if "CPU idle" in name else False,
                               as_timestamp=True)

            plotting_prom.Plot({name: rq},
                               f"Prom: {name}".replace("Control Plane", "Worker"),
                               None,
                               "Count",
                               get_metrics=get_metrics(cluster_role),
                               filter_metrics=no_control_plane_nodes,
                               get_legend_name=get_legend_name,
                               show_queries_in_title=True,
                               show_legend=True,
                               higher_better=True if "CPU idle" in name else False,
                               as_timestamp=True)

    return all_metrics

def _get_plane_nodes(cluster_role, register):
    all_metrics = []
    all_metrics += _get_container_mem_cpu(cluster_role, register, [{f"{cluster_role.title()} ApiServer": dict(namespace="openshift-kube-apiserver", pod=["!~kube-apiserver-guard.*", "kube-apiserver-.*"])}])
    all_metrics += _get_container_mem_cpu(cluster_role, register, [{f"{cluster_role.title()} ETCD": dict(namespace="openshift-etcd", pod=["!~etcd-guard-.*", "etcd-.*"])}])

    return all_metrics

def _get_apiserver_errcodes(cluster_role, register):
    all_metrics = []

    apiserver_request_metrics = [
        {f"{cluster_role.title()} API Server Requests (successes)": 'sum by (code) (increase(apiserver_request_total{code=~"2.."}[2m]))'},
        {f"{cluster_role.title()} API Server Requests (client errors)": 'sum by (code) (increase(apiserver_request_total{code=~"4.."}[2m]))'},
        {f"{cluster_role.title()} API Server Requests (server errors)": 'sum by (code) (increase(apiserver_request_total{code=~"5.."}[2m]))'},
    ]

    apiserver_request_duration_metrics = [{f"{cluster_role.title()} API Server {verb} Requests duration":
                                           f'histogram_quantile(0.99, sum(rate(apiserver_request_duration_seconds_bucket{{apiserver="kube-apiserver", verb="{verb}", subresource!="log"}}[2m])) by (resource,subresource,le)) > 0'}
                                          for verb in ["GET", "PUT", "LIST", "PATCH"]
    ]

    all_metrics += apiserver_request_metrics
    all_metrics += apiserver_request_duration_metrics

    def get_apiserver_request_metrics_legend_name(metric_name, metric_metric):
        return f"code={metric_metric['code']}", None

    def get_apiserver_request_duration_metrics_legend_name(metric_name, metric_metric):
        try:
            res = metric_metric['resource']
        except KeyError:
            return str(metric_metric), None

        if metric_metric.get('subresource'):
            res += f"/{metric_metric['subresource']}"
        return res, None
    if register:

        for metric in apiserver_request_metrics:
            name, rq = list(metric.items())[0]

            if 'server errors' in name and cluster_role == 'sutest':
                lts.register_lts_metric(cluster_role, metric)

            plotting_prom.Plot({name: rq},
                               f"Prom: {name}",
                               None,
                               "Count",
                               get_metrics=get_metrics(cluster_role),
                               get_legend_name=get_apiserver_request_metrics_legend_name,
                               show_queries_in_title=True,
                               show_legend=True,
                               as_timestamp=True)

        for metric in apiserver_request_duration_metrics:
            name, rq = list(metric.items())[0]
            plotting_prom.Plot({name: rq},
                               f"Prom: {name}",
                               None,
                               "Count",
                               get_metrics=get_metrics(cluster_role),
                               get_legend_name=get_apiserver_request_duration_metrics_legend_name,
                               show_queries_in_title=True,
                               show_legend=True,
                               as_timestamp=True)

    return all_metrics

# ---

def _get_load_aware_metrics(cluster_role, register):
    all_metrics = []

    resource_utilisation_metrics = [
        {f"{cluster_role.title()} Node CPU Utilisation rate": 'instance:node_cpu_utilisation:rate1m'},
    ]


    def get_legend_name(metric_name, metric_metric):
        return metric_metric["instance"], None


    def only_workload_nodes(entry, metrics):
        workload_nodes = [node.name for node in entry.results.cluster_info.workload]

        for metric in metrics:
            if metric.metric["instance"] not in workload_nodes:
                continue
            yield metric

    all_metrics += resource_utilisation_metrics

    if register:
        for metric in resource_utilisation_metrics:
            name, rq = list(metric.items())[0]
            plotting_prom.Plot({name: rq},
                               f"Prom: {name}",
                               None,
                               "1 minute rate",
                               get_metrics=get_metrics(cluster_role),
                               filter_metrics=only_workload_nodes,
                               get_legend_name=get_legend_name,
                               show_queries_in_title=True,
                               show_legend=True,
                               as_timestamp=True)

    return all_metrics


# ---

def get_sutest_metrics(register=False):
    cluster_role = "sutest"

    all_metrics = []
    all_metrics += _get_cluster_mem_cpu(cluster_role, register)
    all_metrics += _get_plane_nodes(cluster_role, register)
    all_metrics += _get_apiserver_errcodes(cluster_role, register)
    all_metrics += _get_control_plane_nodes_cpu_usage(cluster_role, register)

    all_metrics += _get_load_aware_metrics(cluster_role, register)
    all_metrics += _get_kepler_metrics(cluster_role, register)

    return all_metrics


# ---

def get_metrics(name):
    def _get_metrics(entry, metric):
        try:
            return entry.results.metrics[name][metric]
        except KeyError:
            return []

    return _get_metrics


def register(only_initialize=False):
    register = not only_initialize
    get_sutest_metrics(register)

# ---

def _get_kepler_metrics(cluster_role, register):
    all_metrics = []

    watt_per_second_to_kWh = 0.000000277777777777778

    power_metrics = [
        {"Power Consumption Per Node (kWh)": f"sum(irate(kepler_node_core_joules_total[1h]) * {watt_per_second_to_kWh}) by (exported_instance)"},
        {"Power Consumption for Cluster (kWh)": f"sum(sum(irate(kepler_node_core_joules_total[1h]) * {watt_per_second_to_kWh}) by (exported_instance))"},
        {"Power Consumption Total (J)": f"sum(sum(kepler_node_core_joules_total) by (exported_instance))"},
        {"Power Test": "instance:node_cpu_utilisation:rate1m"},
    ]

    def all_nodes(entry, metrics):
        workload_nodes = [node.name for node in entry.results.cluster_info.workload]

        for metric in metrics:
            yield metric

    all_metrics += power_metrics

    if register:
        for metric in power_metrics:
            name, rq = list(metric.items())[0]
            plotting_prom.Plot({name: rq},
                               f"Prom: {name}",
                               None,
                               "1 minute rate",
                               get_metrics=get_metrics(cluster_role),
                               filter_metrics=all_nodes,
                               show_queries_in_title=True,
                               show_legend=True,
                               as_timestamp=True)

    return all_metrics
