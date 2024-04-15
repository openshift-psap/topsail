import projects.core.visualizations.helpers.store.prom as core_prom_store
import matrix_benchmarking.plotting.prom as plotting_prom


SUTEST_CONTAINER_LABELS = [
    {"Kueue controller": dict(namespace="redhat-ods-applications", pod="kueue-controller-manager-.*")},
    {"Codeflare controller": dict(namespace="redhat-ods-applications", pod="codeflare-operator-manager-.*")},
]


def get_scheduling_metrics(cluster_role, register):
    def requests():
        metric = {"CPU Request": 'sum(kube_pod_resource_request{namespace="scheduler-load-test", resource="cpu"} or vector(0))'}

        def get_legend_name(metric_name, metric_metric):
            return "", None

        if register:
            name, rq = list(metric.items())[0]

            plotting_prom.Plot(
                {name: rq}, f"Prom: {name}", None, "Cores",
                get_metrics=core_prom_store.get_metrics(cluster_role),
                get_legend_name=get_legend_name,
                show_queries_in_title=True,
                show_legend=False,
                as_timestamp=True
            )
        return [metric]

    def unschedule_pods():
        metric = {"Unschedulable Pods (by plugin)": 'sum by(plugin) (scheduler_unschedulable_pods)'}

        def get_legend_name(metric_name, metric_metric):
            return metric_metric["plugin"], None

        if register:
            name, rq = list(metric.items())[0]

            plotting_prom.Plot(
                {name: rq}, f"Prom: {name}", None, "Count",
                get_metrics=core_prom_store.get_metrics(cluster_role),
                get_legend_name=get_legend_name,
                show_queries_in_title=True,
                show_legend=True,
                as_timestamp=True
            )
        return [metric]

    def schedule_attemps():
        metric = {"Schedule Attempts": 'sum by(result) (increase(scheduler_schedule_attempts_total[5m]))'}

        def get_legend_name(metric_name, metric_metric):
            return f"result={metric_metric['result']}", None

        if register:
            name, rq = list(metric.items())[0]

            plotting_prom.Plot(
                {name: rq}, f"Prom: {name}", None, "Attempt Count",
                get_metrics=core_prom_store.get_metrics(cluster_role),
                get_legend_name=get_legend_name,
                show_queries_in_title=True,
                show_legend=True,
                as_timestamp=True
            )
        return [metric]

    def batch_jobs():
        metrics = [
            {"Batch Jobs Active": 'count (kube_job_status_active{namespace="scheduler-load-test"} > 0) or vector(0)'},
            {"Batch Jobs Complete": 'count (kube_job_status_complete{namespace="scheduler-load-test"} > 0) or vector(0)'},
            {"Batch Jobs Failed": 'count (kube_job_status_failed{namespace="scheduler-load-test"} > 0) or vector(0)'},
        ]

        def get_legend_name(metric_name, metric_metric):
            return metric_name, None

        if register:
            plotting_prom.Plot(
                metrics, f"Prom: Batch Jobs Status", None, "Job Count",
                get_metrics=core_prom_store.get_metrics(cluster_role),
                get_legend_name=get_legend_name,
                show_queries_in_title=False,
                show_legend=True,
                as_timestamp=True
            )

        return metrics

    all_metrics = []
    all_metrics += schedule_attemps()
    all_metrics += batch_jobs()
    all_metrics += unschedule_pods()
    all_metrics += requests()

    return all_metrics


# ---

def get_sutest_metrics(register=False):
    cluster_role = "sutest"

    all_metrics = []
    all_metrics += core_prom_store.get_cluster_metrics(cluster_role, register=register, container_labels=SUTEST_CONTAINER_LABELS, gpu=False)
    all_metrics += get_scheduling_metrics(cluster_role, register)

    all_metrics += [
        {f"{cluster_role.title()} Control Plane Node Resource Request": "sum by (node, resource) (kube_pod_resource_request)"},
        {f"{cluster_role.title()} Control Plane Node Resource Limit": "sum by (node, resource) (kube_pod_resource_limit)"},
    ]

    return all_metrics

def register(only_initialize=False):
    register = not only_initialize

    get_sutest_metrics(register)


def register(only_initialize=False):
    register = not only_initialize
    get_sutest_metrics(register)
