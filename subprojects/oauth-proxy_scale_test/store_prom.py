import matrix_benchmarking.plotting.prom.cpu_memory as plotting_prom_cpu_memory
import matrix_benchmarking.store.prom_db as store_prom_db

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
    labels_str_no_container = _labels_to_string(labels, ["container"]) # the 'container' isn't set for the CPU usage

    metric_name = "_".join(f"{k}={v}" for k, v in labels.items())

    return [
        {f"{cluster_role}__container__cpu__{metric_name}": "pod:container_cpu_usage:sum{"+labels_str_no_container+"}"},
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

def get_test_metrics(register=False):
    cluster_role = "cluster"

    container_labels = [
        {"nginx": dict(namespace="notebook-scale-test-nginx", container="nginx")},
        {"oauth-proxy": dict(namespace="oauth-proxy", pod="cakephp-mysql-example.*", container="oauth-proxy")},
    ]

    all_metrics = []
    all_metrics += _get_container_mem_cpu(cluster_role, register, container_labels)
    return all_metrics

def get_metrics(name):
    def _get_metrics(entry, metric):
        try:
            return entry.results.metrics[name][metric]
        except KeyError:
            return []
    return _get_metrics

def extract_metrics(dirname):
    METRICS = {
        "cluster": ("*__cluster__dump_prometheus_db/prometheus.tar*", get_test_metrics()),
    }

    results_metrics = {}
    for name, (tarball_glob, metrics) in METRICS.items():
        try:
            prom_tarball = list(dirname.glob(tarball_glob))[0]
        except IndexError:
            logging.warning(f"No {tarball_glob} in '{dirname}'.")
            continue

        results_metrics[name] = store_prom_db.extract_metrics(prom_tarball, metrics, dirname)

    return results_metrics
