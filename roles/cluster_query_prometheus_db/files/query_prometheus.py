#! /usr/bin/env python3

import json
import yaml
import sys, os
import subprocess
import pathlib
import urllib3
urllib3.disable_warnings()
import logging
logging.getLogger().setLevel(logging.INFO)
import datetime

import prometheus_api_client
import fire

def get_k8s_token_proxy():
    token_file = pathlib.Path("/run/secrets/kubernetes.io/serviceaccount/token")
    if token_file.exists():
        with open(token_file) as f:
            token = f.read()
        proxy = None

    else:
        kubeconfig_path = os.environ.get("KUBECONFIG")

        if not kubeconfig_path: # this makes it safe if KUBECONFIG == ""
            kubeconfig_path = pathlib.Path(os.environ["HOME"])  / ".kube/config"

        with open(kubeconfig_path) as f:
            kubeconfig = yaml.safe_load(f)

        proxy = kubeconfig["clusters"][0]["cluster"].get("proxy-url")
        token = None

    if token is None:
        token = subprocess.run("oc whoami -t", capture_output=True, text=True, shell=True, check=True).stdout.strip()

    return token, proxy


def get_queries(metrics_file):
    current_name = None
    current_query = None

    queries = []

    with open(metrics_file) as f:
        for line in f.readlines():
            if not line.startswith("#"):
                current_query += line
                continue

            if current_query is not None:
                queries.append(dict(name=current_name, query=current_query.strip()))

            current_name = line[1:].strip()
            current_query = ""

    return queries


def get_prometheus_route():
    if pathlib.Path("/run/secrets/kubernetes.io/serviceaccount/namespace").exists():
        return "prometheus-k8s.openshift-monitoring:9091"

    result = subprocess.run(
        "oc get route -n openshift-monitoring prometheus-k8s -ojsonpath='{.status.ingress[0].host}'",
        capture_output = True, text = True, shell=True,
    )

    return result.stdout.strip()


def fetch_and_save_prometheus_metrics(
        prom_connect, queries, dest,
        namespace,
        duration_s=0, start_ts=None, end_ts=None,
):

    if duration_s:
        up_query = prom_connect.custom_query(query='up[1m]')
        if not up_query:
            logging.error(f"No 'up' metric available. Cannot proceed :/")
            return

        end_ts = up_query[0]["values"][-1][0]
        start_ts = end_ts - duration_s

    ...
    start_date = datetime.datetime.fromtimestamp(start_ts)
    end_date = datetime.datetime.fromtimestamp(end_ts)

    with open(dest / "ts.yaml", "w") as f:
        yaml.dump(dict(start_ts=start_ts, end_ts=end_ts), f)

    with open(dest / "up.json", "w") as f:
        json.dump([dict(metric={}, values=[[start_ts, "1"], [end_ts, "1"]])], f)

    SECOND_PER_STEP = 300
    MIN_STEP = 5
    step = max(MIN_STEP, int(duration_s / SECOND_PER_STEP))

    logging.info(f"Fetching the metrics between {start_date} and {end_date}, with a step of {step} and a duration of {(end_date - start_date).total_seconds()}s...")
    metrics_values = dict()

    def get_filename(query_name):
        return

    for query in queries:
        metric_name = query["name"]
        metric_query = query["query"]
        metric_query = metric_query.replace("$NAMESPACE", namespace)

        metric_file = dest / (query["name"].replace(".*", "") + ".json")
        if metric_file.exists():
            logging.info(f"Already captured: {metric_file.name}")
            continue

        logging.info(f"Fetching {metric_name} ...")
        if "(" in metric_query:
            try:
                values = prom_connect.custom_query_range(query=metric_query, step=step,
                                                         start_time=start_date, end_time=end_date)
            except prometheus_api_client.exceptions.PrometheusApiClientException as e:
                logging.warning(f"Fetching {metric_query} raised an exception")
                logging.warning(f"Exception: {e}")
                continue

            metrics_values[metric_name] = metric_values = []
            if not values: continue
            # deduplicate the values
            for current_values in values:
                current_metric_values = {}
                metric_values.append(current_metric_values)
                current_metric_values["metric"] = current_values["metric"] # empty :/
                current_metric_values["values"] = []
                prev_val = None
                prev_ts = None
                has_skipped = False
                for ts, val in current_values["values"]:
                    prev_ts = ts
                    if val == prev_val:
                        has_skipped = True
                        continue
                    if has_skipped:
                        current_metric_values["values"].append([prev_ts, prev_val])
                        has_skipped = False
                    current_metric_values["values"].append([ts, val])
                    prev_val = val
                if prev_val is not None and has_skipped:
                    # add the last value if the list wasn't empty
                    current_metric_values["values"].append([ts, val])

        else:
            metric_values = metrics_values[metric_name] = prom_connect.get_metric_range_data(
                metric_query,
                start_time=start_date, end_time=end_date
            )

        if not metric_values:
            logging.warning(f"{metric_name} has no data :/")


        with open(metric_file, "w") as f:
            json.dump(metrics_values.get(metric_name, []), f)



def main(promquery_file,
         dest_dir,
         namespace,
         duration_s=0,
         start_ts=None,
         end_ts=None,
         ):
    """
        Query Prometheus with a list of PromQueries read in a file

        The metrics_file is a multi-line list, with first the name of the metric, prefixed with '#'
        Then the definition of the metric, than can spread on multiple lines, until the next # is found.

        Example:
          promquery_file:
            # sutest__cluster_cpu_capacity
            sum(cluster:capacity_cpu_cores:sum)
            # sutest__cluster_memory_requests
               sum(
                    kube_pod_resource_request{resource="memory"}
                    *
                    on(node) group_left(role) (
                      max by (node) (kube_node_role{role=~".+"})
                    )
                  )
            # openshift-operators CPU request
            sum(kube_pod_container_resource_requests{namespace=~'openshift-operators',resource='cpu'})
            # openshift-operators CPU limit
            sum(kube_pod_container_resource_limits{namespace=~'openshift-operators',resource='cpu'})
            # openshift-operators CPU usage
            sum(rate(container_cpu_usage_seconds_total{namespace=~'openshift-operators'}[5m]))

        Args:
          promquery_file: file where the Prometheus Queries are stored. See the example above to understand the format.
          dest_dir: directory where the metrics should be stored
          duration_s: the duration of the history to query
          start_ts: the start timestamp of the history to query. Incompatible with duration_s flag.
          end_ts: the end timestamp of the history to query. Incompatible with duration_s flag.
          namespace: the namespace where the metrics should searched for
        """

    token, proxy = get_k8s_token_proxy()
    if token is None:
        logging.error("No token available in the KUBECONFIG file ...")
        sys.exit(1)

    logging.info("Getting prometheus route ...")
    prometheus_route = get_prometheus_route()

    logging.info("Parsing the queries file ... ...")
    queries = get_queries(promquery_file)

    if proxy:
        logging.info(f"Setting up the proxy ...")
        os.environ["https_proxy"] = proxy

    logging.info(f"Connecting to {prometheus_route}")
    prom_connect = prometheus_api_client.PrometheusConnect(url=f"https://{prometheus_route}", headers=dict(Authorization=f"Bearer {token}"), disable_ssl=True)

    dest = pathlib.Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    logging.info(f"Fetching the metrics")
    fetch_and_save_prometheus_metrics(prom_connect, queries, dest, namespace, duration_s, start_ts, end_ts)


if __name__ == "__main__":
# Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    # Launch CLI, get a runnable
    runnable = None
    try:
        runnable = fire.Fire(main)
    except fire.core.FireExit:
        raise

    # Run the actual workload
    try:
        if hasattr(runnable, "_run"):
            runnable._run()
        else:
            # CLI didn't resolve completely - either by lack of arguments
            # or use of `--help`. This is okay.
            pass
    except SystemExit as e:
        sys.exit(e.code)
