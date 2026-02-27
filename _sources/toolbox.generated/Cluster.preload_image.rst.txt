:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cluster.preload_image


cluster preload_image
=====================

Preload a container image on all the nodes of a cluster.




Parameters
----------


``name``  

* Name to give to the DaemonSet used for preloading the image.


``image``  

* Container image to preload on the nodes.


``namespace``  

* Namespace in which the DaemonSet will be created.

* default value: ``default``


``node_selector_key``  

* NodeSelector key to apply to the DaemonSet.


``node_selector_value``  

* NodeSelector value to apply to the DaemonSet.


``pod_toleration_key``  

* Pod toleration to apply to the DaemonSet.


``pod_toleration_effect``  

* Pod toleration to apply to the DaemonSet.

