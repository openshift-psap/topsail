:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Kwok.set_scale


kwok set_scale
==============

Deploy a set of KWOK nodes




Parameters
----------


``scale``  

* The number of required nodes with given instance type


``taint``  

* Taint to apply to the machineset.


``name``  

* Name to give to the new machineset.

* default value: ``kwok-machine``


``role``  

* Role of the new nodes

* default value: ``worker``


``cpu``  

* Number of CPU allocatable

* default value: ``32``


``memory``  

* Number of Gi of memory allocatable

* default value: ``256``


``gpu``  

* Number of nvidia.com/gpu allocatable


``pods``  

* Number of Pods allocatable

* default value: ``250``

