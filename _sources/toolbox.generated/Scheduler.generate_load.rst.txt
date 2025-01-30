:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Scheduler.generate_load


scheduler generate_load
=======================

Generate scheduler load




Parameters
----------


``namespace``  

* Name of the namespace where the scheduler load will be generated


``base_name``  

* Name prefix for the scheduler resources

* default value: ``sched-test-``


``job_template_name``  

* Name of the job template to use inside the AppWrapper

* default value: ``sleeper``


``aw_states_target``  

* List of expected AppWrapper target states


``aw_states_unexpected``  

* List of AppWrapper states that fail the test


``mode``  

* Mcad, kueue, coscheduling or job

* default value: ``job``


``count``  

* Number of resources to create

* default value: ``3``


``pod_count``  

* Number of Pods to create in each of the AppWrappers

* default value: ``1``


``pod_runtime``  

* Run time parameter to pass to the Pod

* default value: ``30``


``pod_requests``  

* Requests to pass to the Pod definition

* default value: ``{'cpu': '100m'}``


``timespan``  

* Number of minutes over which the resources should be created


``distribution``  

* The distribution method to use to spread the resource creation over the requested timespan

* default value: ``poisson``


``scheduler_load_generator``  

* The path of the scheduler load generator to launch

* default value: ``projects/scheduler/subprojects/scheduler-load-generator/generator.py``


``kueue_queue``  

* The name of the Kueue queue to use

* default value: ``local-queue``


``resource_kind``  

* The kind of resource created by the load generator

* default value: ``job``

