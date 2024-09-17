:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cluster.reset_prometheus_db


cluster reset_prometheus_db
===========================

Resets Prometheus database, by destroying its Pod

By default, target OpenShift Prometheus Pod.


Parameters
----------


``mode``  

* Mode in which the role will run. Can be 'reset' or 'dump'.

* default value: ``reset``


``label``  

* Label to use to identify Prometheus Pod.

* default value: ``app.kubernetes.io/component=prometheus``


``namespace``  

* Namespace where to search Promtheus Pod.

* default value: ``openshift-monitoring``


# Constants
# Prefix to apply to the db name in 'dump' mode
# Defined as a constant in Cluster.reset_prometheus_db
cluster_prometheus_db_dump_name_prefix: prometheus

# Directory to dump on the Prometheus Pod
# Defined as a constant in Cluster.reset_prometheus_db
cluster_prometheus_db_directory: /prometheus
