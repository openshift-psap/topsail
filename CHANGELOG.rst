**What has changed in ci-artifacts?**

(Organized release by release)

Changes since version 0.1 (June 2021)
---------------------------------------

Toolbox
^^^^^^^

- Add nfd test_master_branch protocol `#179 <https://github.com/openshift-psap/ci-artifacts/pull/179>`_

  - new toolbox command: ``toolbox/nfd-operator/deploy_from_commit.sh <git repository> <git reference>`` to deploy NFD Operator from a custom commit.

-  Support for running NTO e2e tests `#185 <https://github.com/openshift-psap/ci-artifacts/pull/185>`_

  - new toolbox command: ``toolbox/nto/run_e2e_test.sh <git repository> <git reference>`` to run the NTO e2e testsuite from a given commit.


Retro-compatibility breaks
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Add nfd test_master_branch protocol `#179 https://github.com/openshift-psap/ci-artifacts/pull/179>`_

Bug fixes
~~~~~~~~~

- Use ``subscriptions.operators.coreos.com`` instead of
  ``subscriptions`` to avoid conflicts with Knative `subscriptions
  <https://knative.dev/docs/eventing/channels/subscriptions>`_ `#207
  <https://github.com/openshift-psap/ci-artifacts/pull/207>`_ `#208
  <https://github.com/openshift-psap/ci-artifacts/pull/208>`_


Features of version 0.1 (June 2021)
-----------------------------------

  - ``toolbox/nfd/deploy_from_operatorhub.sh`` was moved to ``toolbox/nfd-operator/deploy_from_operatorhub.sh``

Bug fixes
^^^^^^^^^

- ``toolbox/local-ci/deploy.sh <ci command> <git repository> <git reference>`` was fixed `#179 <https://github.com/openshift-psap/ci-artifacts/pull/179>`_


Other changes
^^^^^^^^^^^^^

- Introduce a Github Action for checking ansible variable consistency `#196 <https://github.com/openshift-psap/ci-artifacts/pull/196>`_

  - ``toolbox/repo/validate_role_files.py`` is a new script to ensure that all the Ansible variables defining a filepath (``roles/``) do point to an existing file
  - ``toolbox/repo/validate_role_vars_used.py`` is a new script to ensure that all the Ansible variables defined are actually used in their role (with an exception for symlinks)

- gpu_operator_deploy_from_operatorhub: allow overriding subscription.spec.installPlanApproval `#219<https://github.com/openshift-psap/ci-artifacts/pull/219>`_

  - ``./toolbox/gpu-operator/deploy_from_operatorhub.sh`` can receive a new flag ``-install-plan=Manual|Automatic`` (``Manual`` is the default) to override the Subscription install-plan approval setting when deploying from OperatorHub.

Changes since version May 7th, 2021
-----------------------------------

Retro-compatibility breaks
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Change scaleup to set_scale - supported scale other than just 1 node `#139 <https://github.com/openshift-psap/ci-artifacts/pull/139>`_

  - ``toolbox/cluster/scaleup.sh`` has been removed,
  - ``toolbox/cluster/set_scale.sh`` has been `introduced <https://openshift-psap.github.io/ci-artifacts/toolbox/cluster.html#cluster-scale>`_ as a replacement.

- Add easy ways to test the entitlement `#120 <https://github.com/openshift-psap/ci-artifacts/pull/120>`_

  - ``toolbox/entitlement/deploy.sh --machine-configs /path/to/machineconfigs`` has been removed
  - ``toolbox/entitlement/deploy.sh --pem /path/to/key.pem`` should be
    used instead. See `there
    <https://github.com/openshift-psap/ci-artifacts/blob/7aad891ee7c41fea3d31a0152b882fe07d325479/build/root/usr/local/bin/entitle.sh#L13>`_
    for a function to extract the PEM key from a ``machine-configs`` resource file.

- toolbox: rename entitlement/test.sh -> entitlement/test_cluster.sh `#166 <https://github.com/openshift-psap/ci-artifacts/pull/166>`_

  - ``toolbox/entitlement/test.sh`` was renamed into
  - ``toolbox/entitlement/test_cluster.sh``


Other changes
^^^^^^^^^^^^^

- Change scaleup to set_scale - supported scale other than just 1 node `#139 <https://github.com/openshift-psap/ci-artifacts/pull/139>`_

  - ``toolbox/cluster/set_scale.sh`` has been `introduced
    <https://openshift-psap.github.io/ci-artifacts/toolbox/cluster.html#cluster-scale>`_
    to control the scale (node count, of a given AWS instance-type) of
    a cluster

- Add easy ways to test the entitlement `#120 <https://github.com/openshift-psap/ci-artifacts/pull/120>`_

  - new commands to test a PEM key before deploying it:

    - ``toolbox/entitlement/test_in_podman.sh /path/to/key.pem``
    - ``toolbox/entitlement/test_in_cluster.sh /path/to/key.pem``

- gpu_operator_set_repo-config: new role to set spec.driver.repoConfig `#124 <https://github.com/openshift-psap/ci-artifacts/pull/124/files>`_

  - new option to deploy a custom PEM CA file, to access private repo mirrors

    - ``toolbox/entitlement/deploy.sh --pem </path/to/key.pem> [--ca </path/to/key.ca.pem>]``

  - new command to configure the GPU Operator with a given repo-list file

    - ``toolbox/gpu-operator/set_repo-config.sh <path/to/repo.list> [<dest-dir>]``

- gpu_operator_deploy_from_operatorhub: add support for setting the channel `# <https://github.com/openshift-psap/ci-artifacts/pull/173>`

    - ``toolbox/gpu-operator/deploy_from_operatorhub.sh [<version> [<channel>]]``

CI Image and Testing
~~~~~~~~~~~~~~~~~~~~

- gpu_operator_set_repo-config: new role to set spec.driver.repoConfig `#124 <https://github.com/openshift-psap/ci-artifacts/pull/124/files>`_

Bug fixes
~~~~~~~~~

-
