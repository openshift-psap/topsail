:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cluster.dump_prometheus_db


cluster dump_prometheus_db
==========================

Dump Prometheus database into a file

By default, target OpenShift Prometheus Pod.


Parameters
----------


``label``  

* Label to use to identify Prometheus Pod.

* default value: ``app.kubernetes.io/component=prometheus``


``namespace``  

* Namespace where to search Promtheus Pod.

* default value: ``openshift-monitoring``


``dump_name_prefix``  

* Name prefix for the archive that will be stored.

* default value: ``prometheus``


# Constants
# 
# Defined as a constant in Cluster.dump_prometheus_db
cluster_prometheus_db_mode: dump
