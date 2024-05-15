import projects.core.visualizations.helpers.store.prom as core_prom_store
import matrix_benchmarking.plotting.prom.cpu_memory as plotting_prom_cpu_memory

# ---

SUTEST_CONTAINER_LABELS = [
    {"Fine-tuning Pods": dict(namespace="fine-tuning-testing", container="pytorch")},

    {"Kueue controller": dict(namespace="redhat-ods-applications", pod="kueue-controller-manager-.*")},
    {"Codeflare controller": dict(namespace="redhat-ods-applications", pod="codeflare-operator-manager-.*")},
    {"Kubeflow Training operator": dict(namespace="redhat-ods-applications", pod="kubeflow-training-operator-.*")},
]

# ---


# ---

def get_sutest_metrics(register=False):
    cluster_role = "sutest"

    all_metrics = []

    all_metrics += [{"up": "up"}] # for the test start/end timestamp

    all_metrics += core_prom_store.get_cluster_metrics(cluster_role, register=register, container_labels=SUTEST_CONTAINER_LABELS)


    return all_metrics


def register(only_initialize=False):
    register = not only_initialize

    get_sutest_metrics(register)
