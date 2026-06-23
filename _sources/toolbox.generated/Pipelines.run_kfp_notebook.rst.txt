:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Pipelines.run_kfp_notebook


pipelines run_kfp_notebook
==========================

Run a notebook in a given notebook image.




Parameters
----------


``namespace``  

* Namespace in which the notebook will be deployed, if not deploying with RHODS. If empty, use the project return by 'oc project --short'.


``dsp_application_name``  

* The name of the DSPipelines Application to use. If empty, lookup the application name in the namespace.


``imagestream``  

* Imagestream to use to look up the notebook Pod image.

* default value: ``s2i-generic-data-science-notebook``


``imagestream_tag``  

* Imagestream tag to use to look up the notebook Pod image. If emtpy and and the image stream has only one tag, use it. Fails otherwise.


``notebook_name``  

* A prefix to add the name of the notebook to differential notebooks in the same project


``notebook_directory``  

* Directory containing the files to mount in the notebook.

* default value: ``testing/pipelines/notebooks/hello-world``


``notebook_filename``  

* Name of the ipynb notebook file to execute with JupyterLab.

* default value: ``kfp_hello_world.ipynb``


``run_count``  

* Number of times to run the pipeline


``run_delay``  

* Number of seconds to wait before trigger the next run from the notebook


``stop_on_exit``  

* If False, keep the notebook running after the test.

* default value: ``True``


``capture_artifacts``  

* If False, disable the post-test artifact collection.

* default value: ``True``


``capture_prom_db``  

* If True, captures the Prometheus DB of the systems.


``capture_extra_artifacts``  

* Whether to capture extra descriptions and YAML's

* default value: ``True``


``wait_for_run_completion``  

* Whether to wait for one runs completion before starting the next

