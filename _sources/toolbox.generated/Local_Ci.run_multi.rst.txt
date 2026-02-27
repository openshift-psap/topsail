:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Local_Ci.run_multi


local_ci run_multi
==================

Runs a given CI command in parallel from multiple Pods




Parameters
----------


``ci_command``  

* The CI command to run.


``user_count``  

* Batch job parallelism count.
* type: Int

* default value: ``1``


``namespace``  

* The namespace in which the image.

* default value: ``topsail``


``istag``  

* The imagestream tag to use.

* default value: ``topsail:main``


``job_name``  

* The name to give to the Job running the CI command.

* default value: ``topsail``


``service_account``  

* Name of the ServiceAccount to use for running the Pod.

* default value: ``default``


``secret_name``  

* Name of the Secret to mount in the Pod.


``secret_env_key``  

* Name of the environment variable with which the secret path will be exposed in the Pod.


``retrieve_artifacts``  

* If False, do not retrieve locally the test artifacts.


``minio_namespace``  

* Namespace where the Minio server is located.


``minio_bucket_name``  

* Name of the bucket in the Minio server.


``minio_secret_key_key``  

* Key inside 'secret_env_key' containing the secret to access the Minio bucket. Must be in the form 'user_password=SECRET_KEY'.


``variable_overrides``  

* Optional path to the variable_overrides config file (avoids fetching Github PR json).


``use_local_config``  

* If true, gives the local configuration file ($TOPSAIL_FROM_CONFIG_FILE) to the Pods.

* default value: ``True``


``capture_prom_db``  

* If True, captures the Prometheus DB of the systems.
* type: Bool

* default value: ``True``


``git_pull``  

* If True, update the repo in the image with the latest version of the build ref before running the command in the Pods.
* type: Bool


``state_signal_redis_server``  

* Optional address of the Redis server to pass to StateSignal synchronization. If empty, do not perform any synchronization.


``sleep_factor``  

* Delay (in seconds) between the start of each of the users.


``user_batch_size``  

* Number of users to launch after the sleep delay.

* default value: ``1``


``abort_on_failure``  

* If true, let the Job abort the parallel execution on the first Pod failure. If false, ignore the process failure and track the overall failure count with a flag.


``need_all_success``  

* If true, fails the execution if any of the Pods failed. If false, fails it if none of the Pods succeed.


``launch_as_daemon``  

* If true, do not wait for the job to complete. Most of the options above become irrelevant

