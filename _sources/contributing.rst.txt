Contributing
============

Thanks for taking the time to contribute!

The following is a set of guidelines for contributing to ``TOPSAIL``.
These are mostly guidelines, feel free to propose changes to this
document in a pull request.

---

The primary goal of the repository is to serve as a central repository
of the PSAP team's performance and scale test automation.

The secondary goal of the repository is to offer a toolbox for setting
up and configuring clusters, in preparation of performance and scale test execution.


Pull Request Guidelines
-----------------------

- Pull Requests (PRs) need to be ``/approve`` and reviewed ``/lgtm`` by
  PSAP team members before being merged.

- PRs should have a proper description explaining the problem being
  solved, or the new feature being introduced.


Review Guidelines
-----------------

- Reviews can be performed by anyone interested in the good health of
  the repository; but approval and/or ``/lgtm`` is reserved to PSAP
  team members at the moment.

- The main merging criteria is to have a successful test run that
  executes the modified code. Because of the nature of the repository,
  we can't test all the code paths for all PRs.

  - In order to save unnecessary AWS cloud time, the testing is not
    automatically executed by Prow; it must be manually triggered.


Style Guidelines
----------------

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
