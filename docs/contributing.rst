Contributing
============

Thanks for taking the time to contribute!

The following is a set of guidelines for contributing to ``TOPSAIL``.
These are mostly guidelines, feel free to propose changes to this
document in a pull request.

---

The primary goal of the repository is to serve as a central repository of the
PSAP team's performance and scale test automation.

The secondary goal of the repository is to offer a toolbox for setup
and configuration of the cluster for consistently preparing the
systems-under-test for manual experimentation and test development.

Getting Started
---------------

Refer to ``testing/skeleton`` for a simple example of the structure of a new test.

Pull Request Guidelines
~~~~~~~~~~~~~~~~~~~~~~~

- Pull Requests (PRs) need to be ``/approve`` and reviewed ``/lgtm`` by
  PSAP team members before being merged.

- PRs should have a proper description explaining the problem being
  solved, or the new feature being introduced.

- PRs introducing or modifying ``toolbox`` commands should include a
  documentation commit, so that ``docs`` is kept up-to-date.

Review Guidelines
~~~~~~~~~~~~~~~~~

- Reviews can be performed by anyone interested in the good health of
  the repository; but approval and/or ``/lgtm`` is reserved to PSAP
  team members at the moment.

- The main merging criteria is to have a successful test run that executes the modified code. Because of the nature of the repository, we can't test all the code paths for all PRs.

  - In order to save unnecessary AWS cloud time, the testing is not
    automatically executed by Prow; it must be manually triggered.

Style Guidelines
~~~~~~~~~~~~~~~~

YAML style
^^^^^^^^^^

* Align nested lists with their parent's label

.. code-block:: yaml

    - block:
      - name: ...
        block:
        - name: ...

* YAML files use the `.yml` extension

Ansible style
^^^^^^^^^^^^^

We strive to follow Ansible best practices in the different playbooks.

This command is executed as a GitHub-Action hook on all the new PRs,
to help keeping a consistent code style:

.. code-block:: shell

    ansible-lint -v --force-color -c config/ansible-lint.yml playbooks roles

* Try to avoid using ``shell`` tasks as much as possible

  - Make sure that ``set -o pipefail;`` is part of the shell command
    whenever a ``|`` is involved (``ansible-lint`` forgets some of
    them)

  - Redirection into a ``{{ artifact_extra_logs_dir }}`` file is a
    common exception

* Use inline stanza for ``debug`` and ``fail`` tasks, eg:

.. code-block:: yaml

    - name: The GFD did not label the nodes
      fail: msg="The GFD did not label the nodes"

Coding guidelines
~~~~~~~~~~~~~~~~~

* Keep the main log file clean when everything goes right, and store
  all the relevant information in the ``{{ artifact_extra_logs_dir
  }}`` directory, eg:

.. code-block:: yaml

    - name: Inspect the Subscriptions status (debug)
      shell:
        oc describe subscriptions.operators.coreos.com/gpu-operator-certified
           -n openshift-operators
           > {{ artifact_extra_logs_dir }}/gpu_operator_Subscription.log
      failed_when: false

* Include troubleshooting inspection commands whenever
  possible/relevant (see above for an example)

  - mark them as ``failed_when: false`` to ensure that their execution
    doesn't affect the testing
  - add ``(debug)`` in the task name to make it clear that the command
    is not part of the proper testing.

* Use ``ignore_errors: true`` **only** for tracking **known
  failures**.

  - use ``failed_when: false`` to ignore the task return code
  - but whenever possible, write tasks that do not fail, eg:

.. code-block:: yaml

    oc delete --ignore-not-found=true $MY_RESOURCE

* Try to group related modifications in a dedicated commit, and stack
  commits in logical order (eg, 1/ add role, 2/ add toolbox script 3/
  integrate the toolbox scrip in the nightly CI)

  - Commits are not squashed, so please avoid commits "fixing" another
    commit of the PR.
  - Hints: `git revise <https://github.com/mystor/git-revise>`_

    * use ``git revise <commit>`` to modify an older commit (not
      older that ``master`` ;-)
    * use ``git revise --cut <commit>`` to split a commit in two
      logical commits
    * or simply use ``git commit --amend`` to modify the most recent commit


Code contributions
------------------

Creating new roles in Topsail
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

How roles are organized
^^^^^^^^^^^^^^^^^^^^^^^

Roles in Topsail are standard Ansible roles that are wired into the
run_toolbox.py command line interface.

In Topsail, the roles are in the project’s root folder inside the root
folder, their structure is standard to Ansible like the following:

.. code:: bash

   toolbox/
   └── roles-example/
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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Topsail generates automatically all the default parameters in the
``<role>/defaults/main.yml`` file, this is to make sure all the roles
parameters are consistent with what the CLI supports
(``run_toolbox.py``). The file ``<role>/defaults/main.yml`` is rendered
automatically when executing from the project’s root folder
``./run_toolbox.py repo generate_ansible_default_settings``. ###
Including new roles in Topsail’s CLI

1. Creating a Python class for the new role
'''''''''''''''''''''''''''''''''''''''''''

Create a class file to reference the new included role and define the
default parameters that can be referenced from the CLI as parameters.

In the project’s root folder create a ``<new_role_name>.py`` with the
following

::

   import os
   import json

   from topsail._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams
   import ansible_runner

   class <new_role_name_class>:
       """
       Commands relating to <new_role_name>
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

           return RunAnsibleRole(locals())

2. Including the role class in the Toolbox
''''''''''''''''''''''''''''''''''''''''''

To be able to reach new roles from the CLI they need to be registered in
the main ``Toolbox`` class, to do so edit the file ``__init__.py`` and
include

::

   .
   .
   from topsail.<new_role_name> import <new_role_name_class>

   class Toolbox:
       """
       The PSAP Operators Toolbox
       .
       .
       """
       def __init__(self):
           self.cluster = Cluster
           .
           .
           self.<new_role_name> = <new_role_name_class>

Once the new role class is included in the main ``Toolbox`` class it
should be reachable from the ``run_toolbox.py`` CLI.

3. Rendering the default parameters
'''''''''''''''''''''''''''''''''''

Now, once the new role is created, the role class is added to the
project’s root folder and the CLI entrypoint is included in the
``Toolbox`` class, it is possible to render the role default parameters
from the ``run_toolbox.py`` CLI. To render the default parameters for
all roles execute:

::

   ./run_toolbox.py repo generate_ansible_default_settings

4. Executing the new role from the toolbox
''''''''''''''''''''''''''''''''''''''''''

Once the role is in the correct folder and the ``Toolbox`` entrypoints
are up to date, this new role can be executed directly from ``run_toolbox.py``
like:

::

   ./run_toolbox.py <new_role_name> <new_role_parameter_1> <new_role_parameter_n>
