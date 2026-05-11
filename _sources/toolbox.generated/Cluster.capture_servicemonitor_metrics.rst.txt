:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cluster.capture_servicemonitor_metrics


cluster capture_servicemonitor_metrics
======================================

Captures ServiceMonitor or PodMonitor YAML and status for a given service

Captures the ServiceMonitor/PodMonitor configuration and status information for
a specific service in a namespace, including related service/pod and
endpoints information for troubleshooting monitoring setup.


Parameters
----------


``service_name``  

* Name of the service to capture ServiceMonitor/PodMonitor metrics for


``namespace``  

* Namespace where the service and ServiceMonitor/PodMonitor are located (empty string auto-detects current namespace)


``capture_frequency``  

* How often to capture metrics in seconds (default: 15)

* default value: ``60``


``is_podmonitor``  

* Whether to use PodMonitor instead of ServiceMonitor (default: False)


``finalize``  

* Whether to finalize (capture logs and delete) an existing pod instead of creating new one (default: False)

