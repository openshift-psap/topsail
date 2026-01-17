:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Jump_Ci.prepare_step


jump_ci prepare_step
====================

Prepares the jump host for running a CI test step:




Parameters
----------


``cluster``  

* Name of the cluster lock to use


``lock_owner``  

* Name of the lock owner


``project``  

* Name of the project to execute


``step``  

* Name of the step to execute


``env_file``  

* Path to the env file to use


``variables_overrides_dict``  

* Dictionnary to save as the variable overrides file


``secrets_path_env_key``  

* If provided, the env key will be used to locate the secret directories to upload to the jump host

