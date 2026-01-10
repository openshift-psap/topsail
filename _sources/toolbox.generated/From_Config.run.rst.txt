:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: From_Config.run


from_config run
===============

Run ``topsail`` toolbox commands from a single config file.




Parameters
----------


``group``  

* Group from which the command belongs.


``command``  

* Command to call, within the group.


``config_file``  

* Configuration file from which the parameters will be looked up. Can be passed via the TOPSAIL_FROM_CONFIG_FILE environment variable.


``command_args_file``  

* Command argument configuration file. Can be passed via the TOPSAIL_FROM_COMMAND_ARGS_FILE environment variable.


``prefix``  

* Prefix to apply to the role name to lookup the command options.


``suffix``  

* Suffix to apply to the role name to lookup the command options.


``extra``  

* Extra arguments to pass to the commands. Use the dictionnary notation: '{arg1: val1, arg2: val2}'.
* type: Dict


``show_args``  

* Print the generated arguments on stdout and exit, or only a given argument if a value is passed.

