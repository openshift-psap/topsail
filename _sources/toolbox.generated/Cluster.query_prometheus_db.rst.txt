:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cluster.query_prometheus_db


cluster query_prometheus_db
===========================

Query Prometheus with a list of PromQueries read in a file

The metrics_file is a multi-line list, with first the name of the metric, prefixed with '#'
Then the definition of the metric, than can spread on multiple lines, until the next # is found.

Example:
::

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


Parameters
----------


``promquery_file``  

* File where the Prometheus Queries are stored. See the example above to understand the format.


``dest_dir``  

* Directory where the metrics should be stored


``namespace``  

* The namespace where the metrics should searched for


``duration_s``  

* The duration of the history to query


``start_ts``  

* The start timestamp of the history to query. Incompatible with duration_s flag.


``end_ts``  

* The end timestamp of the history to query. Incompatible with duration_s flag.

