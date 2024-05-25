import projects.core.visualizations.helpers.store.prom as core_prom_store
import matrix_benchmarking.plotting.prom.cpu_memory as plotting_prom_cpu_memory

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

# ---

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
                                      get_metrics=core_prom_store.get_metrics(cluster_role),
                                      as_timestamp=True, container_name=namespace,
                                      )
        plotting_prom_cpu_memory.Plot(mem, f"Namespace {namespace}: Mem usage",
                                      get_metrics=core_prom_store.get_metrics(cluster_role),
                                      as_timestamp=True, is_memory=True,
                                      skip_nodes=False,
                                      )

    return all_metrics

# ---

def get_sutest_metrics(register=False):
    cluster_role = "sutest"

    all_metrics = []
    all_metrics += core_prom_store.get_cluster_metrics(cluster_role, register=register, container_labels=SUTEST_CONTAINER_LABELS, gpu_container="kserve-container")
    all_metrics += _get_rhoai_resource_usage(cluster_role, register)

    return all_metrics

def register(only_initialize=False):
    register = not only_initialize

    get_sutest_metrics(register)
