======================
Repository Maintenance
======================

Consistency checks
==================

* Ensure that all the Ansible variables defining a filepath
  (``roles/``) do point to an existing file


.. code-block:: shell

    ./run_toolbox.py repo validate_role_files


* Ensure that all the Ansible variables defined are actually used in
  their role (with an exception for symlinks)


.. code-block:: shell

    ./run_toolbox.py repo validate_role_vars_used
