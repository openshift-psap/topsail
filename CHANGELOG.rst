**What has changed in ci-artifacts?**

(Organized release by release)

Changes since version 1.0.0 (June 2021)
---------------------------------------

Toolbox
^^^^^^^

...

Retro-compatibility breaks
^^^^^^^^^^^^^^^^^^^^^^^^^^

...

Other changes
^^^^^^^^^^^^^

...

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
