How roles are organized
-----------------------

Roles in TOPSAIL are standard Ansible roles that are wired into the
``run_toolbox.py`` command line interface.

In TOPSAIL, the roles are organized by projects, in the
``projects/PROJECT_NAME/roles`` directories. Their structure follows
Ansible standard role guidelines:

.. code:: bash

   toolbox/
   ├── <group name>.py
   └── <new_role_name>/
       ├── defaults
       │   └── main.yml
       ├── files
       │   └── .keep
       ├── README.md
       ├── tasks
       │   └── main.yml
       ├── templates
       │   └── example.yml.j2
       └── vars
           └── main.yml

How default parameters are generated
------------------------------------

Topsail generates automatically all the default parameters in the
``<role>/defaults/main.yml`` file, to make sure all the roles
parameters are consistent with what the CLI supports
(``run_toolbox.py``). The file ``<role>/defaults/main.yml`` is
rendered automatically when executing from the project’s root folder:

::

    ./run_toolbox.py repo generate_toolbox_related_files
    # or
    ./run_toolbox.py repo generate_ansible_default_settings


Including new roles in Topsail’s CLI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Creating a Python class for the new role
"""""""""""""""""""""""""""""""""""""""""""

Create a class file to reference the new role and define the default
parameters that can be referenced from the CLI as parameters.

In the project’s ``toolbox`` directory, create or edit the
``<project_name>.py`` file with the following code:

::

    import sys

    from projects.core.library.ansible_toolbox import (
        RunAnsibleRole, AnsibleRole,
        AnsibleMappedParams, AnsibleConstant,
        AnsibleSkipConfigGeneration
    )

   class <project_name>:
       """
       Commands relating to <project_name>
       """

       @AnsibleRole("<new_role_name>")
       @AnsibleMappedParams
       def run(self,
               <new_role_parameter_1>,
               <new_role_parameter_n>,
               ):
           """
           Run <new_role_name>

           Args:
             <new_role_parameter_1>: First parameter
             <new_role_parameter_n>: Nth parameter
           """

           # if needed, perform simple parameters validation here

           return RunAnsibleRole(locals())

Description of the decorators
'''''''''''''''''''''''''''''

* ``@AnsibleROle(role_name)`` tells the role where the command is implemented
* ``@AnsibleMappedParams`` specifies that the Python arguments should
  be mapped into the Ansible arguments (that's the most common)
* ``@AnsibleSkipConfigGeneration`` specifies that no configuration
  should be generated for this command (usually, it means that another
  command already specifies the arguments, and this one reuses the
  same role with different settings)
* ``@AnsibleConstant(description, name, value)`` specifies a Ansible
  argument without Python equivalent. Can be used to pass flags
  embedded in the function name. Eg: ``dump_prometheus`` and
  ``reset_prometheus``.




2. Including the new toolbox class in the Toolbox
"""""""""""""""""""""""""""""""""""""""""""""""""

This step in not necessary anymore. The ``run_toolbox.py`` command
from the root directory loads the toolbox with this generic call:

::

    projects.core.library.ansible_toolbox.Toolbox()

This class traverses all the ``projects/*/toolbox/*.py`` Python files,
and loads the class with the titled name of the file (simplified code):

::

   for toolbox_file in (TOPSAIL_DIR / "projects").glob("*/toolbox/*.py"):
       toolbox_module = __import__(toolbox_file)
       toolbox_name = name of <toolbox_file> without extension
       toolbox_class = getattr(toolbox_module, toolbox_name.title())


3. Rendering the default parameters
"""""""""""""""""""""""""""""""""""

Now, once the new toolbox command is created, the role class is added to the
project’s root folder and the CLI entrypoint is included in the
``Toolbox`` class, it is possible to render the role default parameters
from the ``run_toolbox.py`` CLI. To render the default parameters for
all roles execute:

::

   ./run_toolbox.py repo generate_ansible_default_settings


TOPSAIL GitHub repository will refuse to merge the PR if this command
has not been called after the Python entrypoint has been modified.

4. Executing the new toolbox command
""""""""""""""""""""""""""""""""""""

Once the role is in the correct folder and the ``Toolbox`` entrypoints
are up to date, this new role can be executed directly from ``run_toolbox.py``
like:

::

   ./run_toolbox.py <project_name> <new_role_name> <new_role_parameter_1> <new_role_parameter_n>
