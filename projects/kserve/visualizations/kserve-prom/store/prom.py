import json

from matrix_benchmarking import common
import matrix_benchmarking.plotting.prom as plotting_prom
import matrix_benchmarking.parsing.prom as parsing_prom
import matrix_benchmarking.plotting.prom.cpu_memory as plotting_prom_cpu_memory

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
        {f"{cluster_role}__container_memory_usage_bytes__{metric_name}": "container_memory_usage_bytes{"+labels_str+"}"},
        {f"{cluster_role}__container_memory_rss__{metric_name}": "container_memory_rss{"+labels_str+"}"},
        {f"{cluster_role}__container_memory_requests__{metric_name}": "kube_pod_container_resource_requests{"+labels_str+",resource='memory'}"},
        {f"{cluster_role}__container_memory_limits__{metric_name}": "kube_pod_container_resource_limits{"+labels_str+",resource='memory'}"},
        {f"{cluster_role}__container_max_memory__{metric_name}": "container_memory_max_usage_bytes{"+labels_str+"}"},
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


def _get_gpu_usage(cluster_role, register):
    all_metrics = []

    gpu_usage_metrics = [
        {f"GPU memory used": 'DCGM_FI_DEV_FB_USED{exported_container="kserve-container"}'},
        {f"GPU memory used (all GPUs)": 'sum(DCGM_FI_DEV_FB_USED{exported_container="kserve-container"})'},
        {f"GPU active computes": 'DCGM_FI_PROF_SM_ACTIVE{exported_container="kserve-container"}'},
        {f"GPU memory transfer utilization": 'DCGM_FI_DEV_MEM_COPY_UTIL{exported_container="kserve-container"}'},
        {f"GPU memory unallocated": 'DCGM_FI_DEV_FB_FREE{exported_container="kserve-container"}'},
        {f"GPU memory transfer (rx)": 'DCGM_FI_PROF_PCIE_RX_BYTES{exported_container="kserve-container"}'},
        {f"GPU memory transfer (tx)": 'DCGM_FI_PROF_PCIE_TX_BYTES{exported_container="kserve-container"}'},
        {f"GPU compute utilization (not 100% accurate)": 'DCGM_FI_DEV_GPU_UTIL{exported_container="kserve-container"}'},
        {f"GPU engine usage (not 100% accurate)": 'DCGM_FI_PROF_GR_ENGINE_ACTIVE{exported_container="kserve-container"}'},
        {f"GPU active fp16 pipe": 'DCGM_FI_PROF_PIPE_FP16_ACTIVE{exported_container="kserve-container"}'},
        {f"GPU active fp32 pipe": 'DCGM_FI_PROF_PIPE_FP32_ACTIVE{exported_container="kserve-container"}'},
        {f"GPU active fp64 pipe": 'DCGM_FI_PROF_PIPE_FP64_ACTIVE{exported_container="kserve-container"}'},

    ]
    all_metrics += gpu_usage_metrics

    def get_legend_name(metric_name, metric_metric):
        name = metric_metric.get('Hostname', "<no hostname>")

        return name, None

    if register:
        for metric in gpu_usage_metrics:
            name, rq = list(metric.items())[0]

            y_divisor = 1

            if rq.startswith("DCGM_FI_DEV_FB_"):
                y_title = f"{name} (in GiB)"
                y_divisor = 1024
            elif rq.startswith("DCGM_FI_PROF_PCIE_"):
                y_title = "Memory transfer (in MiB/s)"
                y_divisor = 1024
            elif rq in ('DCGM_FI_DEV_GPU_UTIL', 'DCGM_FI_PROF_GR_ENGINE_ACTIVE'):
                y_title = "Compute usage (in %)"
                if rq == 'DCGM_FI_PROF_GR_ENGINE_ACTIVE':
                    y_divisor = 0.01
            elif rq == "DCGM_FI_DEV_MEM_COPY_UTIL":
                y_title = "GPU transfer bus usage (in %)"
            elif rq == "DCGM_FI_PROF_SM_ACTIVE":
                y_title = "The ratio of cycles an SM has at least 1 warp assigned (in %)"
                y_divisor = 0.01
            elif rq == "DCGM_FI_PROF_SM_OCCUPANCY":
                y_title = "The ratio of number of warps resident on an SM (in %)."
                y_divisor = 0.01
            elif rq.startswith("DCGM_FI_PROF_PIPE_FP"):
                y_title = "Ratio of cycles the fp pipes are active (in %)."
                y_divisor = 0.01
            else:
                y_title = "(no name)"

            plotting_prom.Plot({name: rq},
                               f"Prom: {name}",
                               None,
                               y_title,
                               get_metrics=get_metrics(cluster_role),
                               get_legend_name=get_legend_name,
                               show_queries_in_title=True,
                               y_divisor=y_divisor,
                               show_legend=True,
                               as_timestamp=True)

    return all_metrics

# ---

SUTEST_CONTAINER_LABELS = [
    {"Serving Runtime kserve container": dict(namespace="kserve.*", container="kserve-container")},
    {"Serving Runtime transformer container [caikit]": dict(namespace="kserve.*", container="transformer-container")},
    {"Serving Runtime istio-proxy container [serverless]": dict(namespace="kserve.*", container="istio-proxy")},
    {"Serving Runtime queue-proxy container [serverless]": dict(namespace="kserve.*", container="queue-proxy")},

    {"KServe Controller [serverless]": dict(namespace="redhat-ods-applications", pod="kserve-controller-manager-.*")},
    {"ODH Model Controller": dict(namespace="redhat-ods-applications", pod="odh-model-controller-.*")},

    {"Istio egress [serverless]": dict(namespace="istio-system", pod="istio-egressgateway-.*")},
    {"Istio ingress [serverless]": dict(namespace="istio-system", pod="istio-ingressgateway-.*")},
    {"Istiod DataScience SMCP [serverless]": dict(namespace="istio-system", pod="istiod-data-science-smcp-.*")},

    {"KNative Activator [serverless]": dict(namespace="knative-serving", pod="activator-.*")},
    {"KNative Autoscaler [serverless]": dict(namespace="knative-serving", pod="autoscaler-.*")},
    {"KNative Autoscaler HPA [serverless]": dict(namespace="knative-serving", pod="autoscaler-hpa-.*")},
    {"KNative Controller [serverless]": dict(namespace="knative-serving", pod="controller-.*")},
    {"KNative Domain-mapping [serverless]": dict(namespace="knative-serving", pod="domain-mapping-.*")},
    {"KNative Domain-mapping Webhook [serverless]": dict(namespace="knative-serving", pod="domainmapping-webhook-.*")},
    {"KNative net-istio-controller [serverless]": dict(namespace="knative-serving", pod="net-istio-controller-.*")},
    {"KNative net-istio-webhook [serverless]": dict(namespace="knative-serving", pod="net-istio-webhook-.*")},
    {"KNative webhook [serverless]": dict(namespace="knative-serving", pod="webhook-.*")},
]

def _get_rhoai_resource_usage(cluster_role, register):
    def get_cpu_resource_usage(namespace):
        return [
            {f"{namespace} CPU request" : "sum(kube_pod_container_resource_requests{namespace=~'"+namespace+"',resource='cpu'})"},
            {f"{namespace} CPU limit" : "sum(kube_pod_container_resource_limits{namespace=~'"+namespace+"',resource='cpu'})"},
            {f"{namespace} CPU usage" : "sum(rate(container_cpu_usage_seconds_total{namespace=~'"+namespace+"'}[5m]))"},
        ]

    def get_mem_resource_usage(namespace):
        return [
            {f"{namespace} memory request" : "sum(kube_pod_container_resource_requests{namespace=~'"+namespace+"',resource='memory'})"},
            {f"{namespace} memory limit" : "sum(kube_pod_container_resource_limits{namespace=~'"+namespace+"',resource='memory'})"},
            {f"{namespace} memory usage": "sum(container_memory_rss{namespace=~'"+namespace+"'})"},
        ]

    all_metrics = []

    namespaces = [
        "redhat-ods-.*",
        "knative-.*",
        "istio-system",
        "openshift-operators",
        "kserve-e2e.*",
    ]

    for namespace in namespaces:
        cpu = get_cpu_resource_usage(namespace)
        mem = get_mem_resource_usage(namespace)

        all_metrics += cpu
        all_metrics += mem

        if not register: continue
        plotting_prom_cpu_memory.Plot(cpu, f"Namespace {namespace}: CPU usage",
                                      get_metrics=get_metrics(cluster_role),
                                      as_timestamp=True, container_name=namespace,
                                      )
        plotting_prom_cpu_memory.Plot(mem, f"Namespace {namespace}: Mem usage",
                                      get_metrics=get_metrics(cluster_role),
                                      as_timestamp=True, is_memory=True,
                                      skip_nodes=False,
                                      )

    return all_metrics


def get_sutest_metrics(register=False):
    cluster_role = "sutest"

    all_metrics = []
    all_metrics += _get_cluster_mem_cpu(cluster_role, register)
    all_metrics += _get_plane_nodes(cluster_role, register)
    all_metrics += _get_apiserver_errcodes(cluster_role, register)
    all_metrics += _get_control_plane_nodes_cpu_usage(cluster_role, register)
    all_metrics += _get_container_mem_cpu(cluster_role, register, SUTEST_CONTAINER_LABELS)
    all_metrics += _get_gpu_usage(cluster_role, register)
    all_metrics += _get_rhoai_resource_usage(cluster_role, register)

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
