:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Notebooks.locust_scale_test


notebooks locust_scale_test
===========================

End-to-end testing of RHOAI notebooks at scale, at API level




Parameters
----------


``namespace``  

* Namespace where the test will run


``idp_name``  

* Name of the identity provider to use.


``secret_properties_file``  

* Path of a file containing the properties of LDAP secrets. (See 'deploy_ldap' command).


``test_name``  

* Test to perform.


``minio_namespace``  

* Namespace where the Minio server is located.


``minio_bucket_name``  

* Name of the bucket in the Minio server.


``username_prefix``  

* Prefix of the RHODS users.


``user_count``  

* Number of users to run in parallel.
* type: Int


``user_index_offset``  

* Offset to add to the user index to compute the user name.
* type: Int


``locust_istag``  

* Imagestream tag of the locust container.


``artifacts_exporter_istag``  

* Imagestream tag of the artifacts exporter side-car container.


``run_time``  

* Test run time (eg, 300s, 20m, 3h, 1h30m, etc.)

* default value: ``1m``


``spawn_rate``  

* Rate to spawn users at (users per second)

* default value: ``1``


``sut_cluster_kubeconfig``  

* Path of the system-under-test cluster's Kubeconfig. If provided, the RHODS endpoints will be looked up in this cluster.


``notebook_image_name``  

* Name of the RHODS image to use when launching the notebooks.

* default value: ``s2i-generic-data-science-notebook``


``notebook_size_name``  

* Size name of the notebook.

* default value: ``Small``


``toleration_key``  

* Toleration key to use for the test Pods.


``cpu_count``  

* Number of Locust processes to launch (one per Pod with 1cpu).
* type: Int

* default value: ``1``


``user_sleep_factor``  

* Delay to sleep between users
* type: Float

* default value: ``1.0``


``capture_prom_db``  

* If True, captures the Prometheus DB of the systems.
* type: Bool

* default value: ``True``

