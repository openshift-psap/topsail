from collections import defaultdict

import matrix_benchmarking.plotting.prom as plotting_prom
import matrix_benchmarking.parsing.prom as parsing_prom
import matrix_benchmarking.plotting.prom.cpu_memory as plotting_prom_cpu_memory

def _get_container_cpu(cluster_role, **kwargs):
    labels = ",".join(f"{k}=~'{v}'" for k, v in kwargs.items())
    labels_no_container = ",".join(f"{k}=~'{v}'" for k, v in kwargs.items() if k != "container") # the 'container' isn't set for the CPU usage
    metric_name = "_".join(f"{k}={v}" for k, v in kwargs.items())

    return [
        {f"{cluster_role}__container_cpu__{metric_name}": "pod:container_cpu_usage:sum{"+labels_no_container+"}"},
        {f"{cluster_role}__container_cpu_requests__{metric_name}": "kube_pod_container_resource_requests{"+labels+",resource='cpu'}"},
        {f"{cluster_role}__container_cpu_limits__{metric_name}": "kube_pod_container_resource_limits{"+labels+",resource='cpu'}"},
    ]

def _get_container_mem(cluster_role, **kwargs):
    labels = ",".join(f"{k}=~'{v}'" for k, v in kwargs.items())
    metric_name = "_".join(f"{k}={v}" for k, v in kwargs.items())

    return [
        {f"{cluster_role}__container_memory__{metric_name}": "container_memory_rss{"+labels+"}"},
        {f"{cluster_role}__container_memory_requests__{metric_name}": "kube_pod_container_resource_requests{"+labels+",resource='memory'}"},
        {f"{cluster_role}__container_memory_limits__{metric_name}": "kube_pod_container_resource_limits{"+labels+",resource='memory'}"},
    ]

def _get_container_cpu_mem(**kwargs):
    return _get_container_mem(**kwargs) + _get_container_mem(**kwargs)

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

        mem = _get_container_mem(cluster_role, **labels)
        cpu = _get_container_cpu(cluster_role, **labels)

        all_metrics += mem
        all_metrics += cpu

        if not register: continue

        container = labels.get("container", "all")

        plotting_prom_cpu_memory.Plot(cpu, f"{plot_name}: CPU usage",
                           get_metrics=get_metrics(cluster_role),
                           as_timestamp=True, container_name=container)
        plotting_prom_cpu_memory.Plot(mem, f"{plot_name}: Mem usage",
                           get_metrics=get_metrics(cluster_role),
                           as_timestamp=True, is_memory=True)

    return all_metrics


def _get_master_nodes_cpu_usage(cluster_role, register):
    all_metrics = [
        {f"{cluster_role.title()} Master Node CPU usage" : 'sum(irate(node_cpu_seconds_total[2m])) by (mode, instance) '},
        {f"{cluster_role.title()} Master Node CPU idle" : 'sum(irate(node_cpu_seconds_total{mode="idle"}[2m])) by (mode, instance) '},
    ]

    def get_legend_name(metric_name, metric_metric):
        return metric_metric['mode'], metric_metric['instance']

    def filter_metrics(entry, metrics):
        master_nodes = [node.name for node in entry.results.rhods_cluster_info.master]
        for metric in metrics:
            if metric["metric"]["instance"] not in master_nodes:
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
                               filter_metrics=filter_metrics,
                               get_legend_name=get_legend_name,
                               show_queries_in_title=True,
                               show_legend=True,
                               as_timestamp=True)

    return all_metrics

def _get_master(cluster_role, register):
    all_metrics = []
    all_metrics += _get_container_mem_cpu(cluster_role, register, [{f"{cluster_role.title()} ApiServer": dict(namespace="openshift-kube-apiserver", pod="kube-apiserver-ip-.*")}])
    all_metrics += _get_container_mem_cpu(cluster_role, register, [{f"{cluster_role.title()} ETCD": dict(namespace="openshift-etcd", pod="etcd-ip-.*")}])

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


def _get_authentication(cluster_role, register):
    basic_auth_metrics = [
        {"openshift_auth_basic_password_count": "sum (openshift_auth_basic_password_count)"},
        {"openshift_auth_basic_password_count_result": "sum by (result) (openshift_auth_basic_password_count_result)"},
    ]
    form_auth_metrics = [
        {"openshift_auth_form_password_count": "sum (openshift_auth_form_password_count)"},
        {"openshift_auth_form_password_count_result": "sum by (result) (openshift_auth_form_password_count_result)"},
    ]

    def get_basic_auth_legend_name(metric_name, metric_metric):

        group = "Basic Auth Count"
        if metric_name == "openshift_auth_basic_password_count":
            name = "total"

        elif metric_name == "openshift_auth_basic_password_count_result":
            name = metric_metric["result"]

        return name, group

    def get_form_auth_legend_name(metric_name, metric_metric):
        name = metric_name
        group = "Form Auth Count"
        if metric_name == "openshift_auth_form_password_count":
            name = "total"

        elif metric_name == "openshift_auth_form_password_count_result":
            name = metric_metric["result"]

        return name, group

    if register:
        plotting_prom.Plot(basic_auth_metrics,
                           "OCP: Basic Auth Metrics",
                           None,
                           "Count",
                           get_metrics=get_metrics(cluster_role),
                           get_legend_name=get_basic_auth_legend_name,
                           as_timestamp=True)

        plotting_prom.Plot(form_auth_metrics,
                           "OCP: Form Auth Metrics",
                           None,
                           "Count",
                           get_metrics=get_metrics(cluster_role),
                           get_legend_name=get_form_auth_legend_name,
                           as_timestamp=True)

    return basic_auth_metrics + form_auth_metrics
# ---

def get_sutest_metrics(register=False):
    cluster_role = "sutest"

    container_labels = [
        {"Notebooks": dict(namespace="rhods-notebooks", container="jupyter-nb-psapuser.*")},
        {"OpenLDAP": dict(namespace="openldap", pod="openldap.*")},
        {"RHODS Dashboard": dict(namespace="redhat-ods-applications", pod="rhods-dashboard.*", container="rhods-dashboard")},
        {"KF Notebook Controller": dict(namespace="redhat-ods-applications", pod="notebook-controller-deployment.*")},
        {"ODH Notebook Controller": dict(namespace="redhat-ods-applications", pod="odh-notebook-controller-manager.*")},
        {"OpenShift Authentication": dict(namespace="openshift-authentication", pod="oauth-openshift.*")},
    ]
    all_metrics = []
    all_metrics += _get_cluster_mem_cpu(cluster_role, register)
    all_metrics += _get_container_mem_cpu(cluster_role, register, container_labels)
    all_metrics += _get_authentication(cluster_role, register)
    all_metrics += _get_master(cluster_role, register)
    all_metrics += _get_apiserver_errcodes(cluster_role, register)
    all_metrics += _get_master_nodes_cpu_usage(cluster_role, register)

    return all_metrics


def get_driver_metrics(register=False):
    cluster_role = "driver"

    container_labels = [
        {"Test Pods": dict(namespace="loadtest", container="main")},
    ]
    all_metrics = []
    all_metrics += _get_cluster_mem_cpu(cluster_role, register)
    all_metrics += _get_container_mem_cpu(cluster_role, register, container_labels)
    all_metrics += _get_master(cluster_role, register)

    return all_metrics


def _get_rhods_user_metrics(register=False):
    user_count_metrics = [
        "rhods_total_users", # Number of RHODS users
        {"rhods_new_user_per_minute": 'irate(rhods_total_users[1m])*60'}, # New users per minute
    ]
    def get_user_count_legend_name(metric_name, metric_metric):
        if metric_name == "rhods_total_users":
            return "User count", None
        else:
            return "New users<br>(per minutes)", None

    if register:
        plotting_prom.Plot(user_count_metrics,
                           "RHODS: User Count and Joining Rate",
                           None,
                           "Users",
                           get_metrics=get_metrics("rhods"),
                           as_timestamp=True,
                           get_legend_name=get_user_count_legend_name,
                           )

    return user_count_metrics

def _get_rhods_pod_resource_metrics(register=False):
    pod_cpu_usage_metrics = [
        {"rhods_pod_cpu_usage": 'irate(process_cpu_seconds_total[1m])'}
    ]
    pod_mem_usage_metrics = [
        {'process_virtual_memory_bytes': 'process_virtual_memory_bytes{job!="prometheus"}'},
        {'process_resident_memory_bytes': 'process_resident_memory_bytes{job!="prometheus"}'},
    ]
    pod_fds_usage_metrics = [
        {'process_open_fds': 'process_open_fds{job!="prometheus"}'},
        {'process_max_fds': 'process_max_fds{job!="prometheus"}'},
    ]
    pod_disk_usage_metrics = [
        {"notebooks_pvc_disk_usage": 'kubelet_volume_stats_used_bytes{namespace="rhods-notebooks"}'},
    ]

    def get_resource_legend_name(metric_name, metric_metric):
        group = metric_metric["job"]
        if "memory" in metric_name:
            group += "/" + ("vm" if metric_name == "process_virtual_memory_bytes" else "res")

        return metric_metric["instance"], group

    def get_disk_usage_legend_name(metric_name, metric_metric):
        return metric_metric["persistentvolumeclaim"], metric_metric["node"]

    if register:
        plotting_prom.Plot(pod_cpu_usage_metrics,
                           "RHODS: Pods CPU Usage",
                           None,
                           "CPU usage (in %)",
                           get_metrics=get_metrics("rhods"),
                           as_timestamp=True,
                           get_legend_name=get_resource_legend_name,
                           )
        plotting_prom.Plot(pod_mem_usage_metrics,
                           "RHODS: Pods Memory Usage",
                           None,
                           "Memory usage (in Gi)",
                           get_metrics=get_metrics("rhods"),
                           as_timestamp=True,
                           get_legend_name=get_resource_legend_name,
                           y_divisor=1024*1024*1024,
                           )

        plotting_prom.Plot(pod_disk_usage_metrics,
                           "RHODS: Notebooks PVC Disk Usage",
                           None,
                           "PVC disk usage (in Gi)",
                           get_metrics=get_metrics("rhods"),
                           get_legend_name=get_disk_usage_legend_name,
                           as_timestamp=True,
                           y_divisor=1024*1024,
                           )

    return (pod_cpu_usage_metrics
            + pod_mem_usage_metrics
            + pod_fds_usage_metrics
            + pod_disk_usage_metrics)


def _get_rhods_notebook_metrics(register=False):
    notebook_creation_delay_metrics = [
        {"reason_notebooks_delayed": 'sum by (reason) (kube_pod_container_status_waiting_reason{namespace="rhods-notebooks"})'},
    ]
    notebook_servers_running_metrics = [
        "jupyterhub_running_servers",
    ]
    notebook_spawn_time_metrics = [
        {"successful_notebook_spawn_time": 'jupyterhub_server_spawn_duration_seconds_bucket{status="success"}'},
    ]
    notebook_spawn_count_metrics = [
        {"successful_notebook_spawn_count": 'sum by (status) (jupyterhub_server_spawn_duration_seconds_bucket{status="success"})'},
        {"failed_notebook_spawn_count": 'sum by (status) (jupyterhub_server_spawn_duration_seconds_bucket{status!="success"})'},
    ]

    def get_reason_legend_name(metric_name, metric_metric):
        return metric_metric["reason"], None

    def get_spawn_count_legend_name(metric_name, metric_metric):
        if metric_name == "successful_notebook_spawn_time":
            return f"Less than {metric_metric['le']}", None
        else:
            return metric_metric["status"], None

    if register:
        plotting_prom.Plot(notebook_creation_delay_metrics,
                           "RHODS: Reasons Why Notebooks Are Waiting",
                           None,
                           "Notebook Servers Waiting",
                           get_metrics=get_metrics("rhods"),
                           get_legend_name=get_reason_legend_name,
                           as_timestamp=True,
                           )

    return ([]
            + notebook_creation_delay_metrics
            + notebook_servers_running_metrics
            + notebook_spawn_time_metrics
            + notebook_spawn_count_metrics
            )


def get_rhods_metrics(register=False):
    return ([]
            + _get_rhods_user_metrics(register)
            + _get_rhods_pod_resource_metrics(register)
            + _get_rhods_notebook_metrics(register)
            )

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
