import logging


from . import run

def prepare_light_cluster():
    run.run_toolbox("cluster", "wait_fully_awake")


def cleanup_cluster():
    busy_cluster_ns_label_key = "busy-cluster.topsail"
    busy_cluster_ns_label_value = "yes"
    has_busy_cluster_ns = run.run(f"oc get ns -oname -l{busy_cluster_ns_label_key}={busy_cluster_ns_label_value}", capture_stdout=True).stdout
    if not has_busy_cluster_ns:
        logging.info("No busy-cluster namespace detected, nothing to cleanup.")
        return

    logging.info(f"Detected {len(has_busy_cluster_ns.split())} busy-cluster namespaces. Running the cleanup.")

    run.run_toolbox("busy_cluster", "cleanup")
