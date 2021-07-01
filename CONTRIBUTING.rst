First off, thanks for taking the time to contribute!

The following is a set of guidelines for contributing to Red Hat
OpenShift PSAP ``ci-artifacts``. These are mostly guidelines, not
rules. Use your best judgment, and feel free to propose changes to
this document in a pull request.

---

The primary goal of the repository is to host the tools required for
the nightly testing of the OpenShift operators under Red Hat PSAP team
responsibility, and in particular, NVIDIA GPU Operator and the Special
Resource Operator (SRO).

The OpenShift version we are supporting is 4.N, 4.N-1 and 4.N-2, where 4.N is
the current latest version released. So as of May 2021, we need to
support 4.7, 4.6 and 4.5.

The secondary goal of the repository is to offer a toolbox for
interacting with our operators, and configuring the cluster as required.

Pull Request Guidelines
-----------------------

- Pull Requests (PRs) need to be ``/approve`` and reviewed ``/lgtm`` by
  PSAP team members before being merged.

- PRs should have a proper description explaining the problem being
  solved, or the new feature being introduced.

- PRs introducing or modifying ``toolbox`` commands should include a
  documentation commit, so that ``docs`` is kept up-to-date.

Review Guidelines
-----------------

- Reviews can be performed by anyone interested in the good health of
  the repository; but approval and/or ``/lgtm`` is reserved to PSAP
  team members at the moment.

- Reviewers should ensure that the relevant testing (only ``/test
  gpu-operator-e2e`` at the moment) has been successfully executing
  before the PR can be merged.

  - In order to save unnecessary AWS cloud time, the testing is not
    automatically executed by Prow; it must be manually triggered.
  - ``OpenShift GitHub Bot`` will not merge a PR when the
    ``gpu-operator-e2e`` test failed, but it will merged it if it was
    *never* executed (or if it completed successfully, of course)

Style Guidelines
----------------

YAML style
~~~~~~~~~~

* Align nested lists with their parent's label

.. code-block:: yaml

    - block:
      - name: ...
        block:
        - name: ...

* YAML files use the `.yml` extension

Ansible style
~~~~~~~~~~~~~

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
-----------------

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

Getting Started
---------------

* Duplicate the ``template`` role to prepare the skeleton the new role

* The ``gpu_operator_run_gpu-burn`` role can be studied an example of
  a standalone role & toolbox script. New features should follow a
  similar model:

.. code-block:: shell

    roles/gpu_operator_run_gpu-burn

1. Define the tasks of the new role:

.. code-block:: shell

    ├── tasks
    │   └── main.yml

2. Define the role dependencies (at least ``check_deps``):

.. code-block:: shell

    ├── meta
    │   └── main.yml

3. Define the role configuration variables and their default values:

.. code-block:: shell

    ├── defaults
    │   └── main
    │       └── config.yml

4. Define the script *constant* variables

.. code-block:: shell

    ├── files
    │   ├── gpu_burn_cm_entrypoint.yml
    │   └── gpu_burn_pod.yml
    └── vars
        └── main
            └── resources.yml

5. Add a toolbox script entrypoint setting the role configuration variables

.. code-block:: shell

    toolbox/gpu-operator/
    └── run_gpu_burn.sh

6. If relevant, call the toolbox script from the right nightly CI
   entrypoint:

.. code-block:: shell

    # in build/root/usr/local/bin/ci_entrypoint_gpu-operator.sh

    validate_gpu_operator_deployment() {
        ...
        toolbox/gpu-operator/run_gpu_burn.sh
    }
