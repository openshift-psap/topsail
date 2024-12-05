:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Notebooks.ods_ci_scale_test


notebooks ods_ci_scale_test
===========================

End-to-end scale testing of ROAI notebooks, at user level.




Parameters
----------


``namespace``  

* Namespace in which the scale test should be deployed.


``idp_name``  

* Name of the identity provider to use.


``username_prefix``  

* Prefix of the usernames to use to run the scale test.


``user_count``  

* Number of users to run in parallel.
* type: Int


``secret_properties_file``  

* Path of a file containing the properties of LDAP secrets. (See 'deploy_ldap' command)


``notebook_url``  

* URL from which the notebook will be downloaded.


``minio_namespace``  

* Namespace where the Minio server is located.


``minio_bucket_name``  

* Name of the bucket in the Minio server.


``user_index_offset``  

* Offset to add to the user index to compute the user name.
* type: Int


``sut_cluster_kubeconfig``  

* Path of the system-under-test cluster's Kubeconfig. If provided, the RHODS endpoints will be looked up in this cluster.


``artifacts_collected``  

* - 'all' - 'no-screenshot' - 'no-screenshot-except-zero' - 'no-screenshot-except-failed' - 'no-screenshot-except-failed-and-zero' - 'none'

* default value: ``all``


``user_sleep_factor``  

* Delay to sleep between users

* default value: ``1.0``


``user_batch_size``  

* Number of users to launch at the same time.
* type: Int

* default value: ``1``


``ods_ci_istag``  

* Imagestream tag of the ODS-CI container image.


``ods_ci_exclude_tags``  

* Tags to exclude in the ODS-CI test case.

* default value: ``None``


``ods_ci_test_case``  

* Robot test case name.

* default value: ``notebook_dsg_test.robot``


``artifacts_exporter_istag``  

* Imagestream tag of the artifacts exporter side-car container image.


``notebook_image_name``  

* Notebook image name.

* default value: ``s2i-generic-data-science-notebook``


``notebook_size_name``  

* Notebook size.

* default value: ``Small``


``notebook_benchmark_name``  

* Benchmark script file name to execute in the notebook.

* default value: ``pyperf_bm_go.py``


``notebook_benchmark_number``  

* Number of the benchmarks executions per repeat.

* default value: ``20``


``notebook_benchmark_repeat``  

* Number of the benchmark repeats to execute.

* default value: ``2``


``state_signal_redis_server``  

* Hostname and port of the Redis server for StateSignal synchronization (for the synchronization of the beginning of the user simulation)


``toleration_key``  

* Toleration key to use for the test Pods.


``capture_prom_db``  

* If True, captures the Prometheus DB of the systems.
* type: Bool

* default value: ``True``


``stop_notebooks_on_exit``  

* If False, keep the user notebooks running at the end of the test.
* type: Bool

* default value: ``True``


``only_create_notebooks``  

* If True, only create the notebooks, but don't start them. This will overwrite the value of 'ods_ci_exclude_tags'.
* type: Bool


``driver_running_on_spot``  

* If True, consider that the driver Pods are running on Spot instances and can disappear at any time.
* type: Bool

