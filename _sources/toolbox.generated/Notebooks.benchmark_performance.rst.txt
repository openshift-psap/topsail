:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Notebooks.benchmark_performance


notebooks benchmark_performance
===============================

Benchmark the performance of a notebook image.




Parameters
----------


``namespace``  

* Namespace in which the notebook will be deployed, if not deploying with RHODS.

* default value: ``rhods-notebooks``


``imagestream``  

* Imagestream to use to look up the notebook Pod image.

* default value: ``s2i-generic-data-science-notebook``


``imagestream_tag``  

* Imagestream tag to use to look up the notebook Pod image. If emtpy and and the image stream has only one tag, use it. Fails otherwise.


``notebook_directory``  

* Directory containing the files to mount in the notebook.

* default value: ``projects/notebooks/testing/notebooks/``


``notebook_filename``  

* Name of the ipynb notebook file to execute with JupyterLab.

* default value: ``benchmark_entrypoint.ipynb``


``benchmark_name``  

* Name of the benchmark to execute in the notebook.

* default value: ``pyperf_bm_go.py``


``benchmark_repeat``  

* Number of repeats of the benchmark to perform for one time measurement.
* type: Int

* default value: ``1``


``benchmark_number``  

* Number of times the benchmark time measurement should be done.
* type: Int

* default value: ``1``

