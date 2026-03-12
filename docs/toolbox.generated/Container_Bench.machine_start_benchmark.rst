:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Container_Bench.machine_start_benchmark


container_bench machine_start_benchmark
=======================================

Runs the podman machine start benchmark after first boot with the given runtime properties of exec_props: binary_path:     path to the podman binary rootfull:        whether to run Ansible tasks as root additional_args: additional arguments to pass to the podman binary exec_time_path:  path to the exec_time.py script machine_cpus:         number of CPUs to allocate to the benchmark machine (optional) machine_memory:        memory in MB to allocate to the benchmark machine (optional) machine_rootful:       whether the podman machine runs in rootful mode (default: false)

The benchmark initializes a new podman machine named 'benchmark-machine',
applies the given cpu/memory/rootful configuration via 'podman machine set',
performs a first start and stop to warm up the machine,
then measures the time taken to start it again with 'podman machine start'.
The machine is cleaned up (stopped and removed) after each run.


Parameters
----------


``exec_props``  

* Dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path, machine_cpus, machine_memory, machine_rootful)

