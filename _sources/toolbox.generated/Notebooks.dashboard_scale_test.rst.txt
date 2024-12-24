:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Notebooks.dashboard_scale_test


notebooks dashboard_scale_test
==============================

End-to-end scale testing of ROAI dashboard scale test, at user level.




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


``minio_namespace``  

* Namespace where the Minio server is located.


``minio_bucket_name``  

* Name of the bucket in the Minio server.


``user_index_offset``  

* Offset to add to the user index to compute the user name.
* type: Int


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


``ods_ci_test_case``  

* ODS-CI test case to execute.

* default value: ``notebook_dsg_test.robot``


``artifacts_exporter_istag``  

* Imagestream tag of the artifacts exporter side-car container image.


``state_signal_redis_server``  

* Hostname and port of the Redis server for StateSignal synchronization (for the synchronization of the beginning of the user simulation)


``toleration_key``  

* Toleration key to use for the test Pods.


``capture_prom_db``  

* If True, captures the Prometheus DB of the systems.
* type: Bool

* default value: ``True``

