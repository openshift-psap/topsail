:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Local_Ci.run


local_ci run
============

Runs a given CI command




Parameters
----------


``ci_command``  

* The CI command to run.


``pr_number``  

* The ID of the PR to use for the repository.


``git_repo``  

* The Github repo to use.

* default value: ``https://github.com/openshift-psap/topsail``


``git_ref``  

* The Github ref to use.

* default value: ``main``


``namespace``  

* The namespace in which the image.

* default value: ``topsail``


``istag``  

* The imagestream tag to use.

* default value: ``topsail:main``


``pod_name``  

* The name to give to the Pod running the CI command.

* default value: ``topsail``


``service_account``  

* Name of the ServiceAccount to use for running the Pod.

* default value: ``default``


``secret_name``  

* Name of the Secret to mount in the Pod.


``secret_env_key``  

* Name of the environment variable with which the secret path will be exposed in the Pod.


``test_name``  

* Name of the test being executed.

* default value: ``local-ci-test``


``test_args``  

* List of arguments to give to the test.


``test_description``  

* A text file to upload along with the artifacts, that can describe what is being tested


``init_command``  

* Command to run in the container before running anything else.


``export_bucket_name``  

* Name of the S3 bucket where the artifacts should be exported.


``export_test_run_identifier``  

* Identifier of the test being executed (will be a dirname).

* default value: ``default``


``export``  

* If True, exports the artifacts to the S3 bucket. If False, do not run the export command.

* default value: ``True``


``retrieve_artifacts``  

* If False, do not retrieve locally the test artifacts.

* default value: ``True``


``pr_config``  

* Optional path to a PR config file (avoids fetching Github PR json).


``update_git``  

* If True, updates the git repo with the latest main/PR before running the test.

* default value: ``True``

