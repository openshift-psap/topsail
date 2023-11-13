TOPSAIL
=======

Test Orchestrator for Performance and Scalability of AI pLatforms

|lint| |nbsp| |consistency| |nbsp| |render_ansible| |nbsp| |render_docs|

This repository contains `Ansible <https://www.ansible.com/>`_ roles and
playbooks for interacting with `OpenShift <https://www.openshift.com/>`_ for automating
tasks involved in the performance and scalability tests done by the 
Red Hat PSAP (Performance and Scale for AI Platforms) team.

Documentation
-------------

🚧 Note: Docs are under construction 🚧

See the `documentation pages
<https://openshift-psap.github.io/topsail/index.html>`_. 

Dependencies
------------

The recommended way to run TOPSAIL is via Podman. See `build/Dockerfile`.

Requirements:

- See requirements.txt for reference

.. code-block:: shell

    pip3 install -r requirements.txt
    dnf install jq


- OpenShift Client (``oc``)

.. code-block:: shell

    wget --quiet https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/latest/openshift-client-linux.tar.gz
    tar xf openshift-client-linux.tar.gz oc


- An OpenShift cluster accessible with ``$KUBECONFIG`` properly set

.. code-block:: shell

    oc version # fails if the cluster is not reachable


Prow CI
-------

Several of the performance and scale tests automated in this repository 
are configured to run via the OpenShift PROW instance. These tests are
controlled by the configuration files located in these directories:

* https://github.com/openshift/release/tree/master/ci-operator/config/openshift-psap/topsail
* https://github.com/openshift/release/tree/master/ci-operator/jobs/openshift-psap/topsail

The main configuration is written in the ``config`` directory, and
``jobs`` are then generated with ``make ci-operator-config
jobs``. Secondary configuration options can then be modified in the
``jobs`` directory.


The Prow CI jobs run in an OpenShift Pod. The `ContainerFile
<build/Dockerfile>`_ is used to build their base-image, and the
``run ...`` command is used as entrypoint.

From this entrypoint, the steps of different tests can be executed, for example:

* ``run notebooks prepare_ci``
* ``run notebooks run_ci``
* ``run lightspeed run_ci``
* ``run watsonx-serving test test_ci``


Toolbox
----------------------

The toolbox is a way to interact with the various tasks that are automated with Ansible in the `roles/`` directory

The entrypoint for the toolbox is the `./run_toolbox.py <run_toolbox.py>`_ at the root
of this repository. Run it without any arguments to see the list of
available commands.

The functionalities of the toolbox commands are described in the
`🚧 under construction 🚧 documentation page
<https://openshift-psap.github.io/ci-artifacts/index.html#psap-toolbox>`_.


.. |lint| image:: https://github.com/openshift-psap/topsail/actions/workflows/ansible-lint.yml/badge.svg?event=schedule
    :alt: Linters build status
    :target: https://github.com/openshift-psap/topsail/actions/workflows/ansible-lint.yml
.. |consistency| image:: https://github.com/openshift-psap/topsail/actions/workflows/check_consistency.yml/badge.svg?event=schedule
    :alt: Consistency build status
    :target: https://github.com/openshift-psap/topsail/actions/workflows/check_consistency.yml
.. |render_ansible| image:: https://github.com/openshift-psap/topsail/actions/workflows/check_generated_ansible.yml/badge.svg?event=schedule
    :alt: Render Ansible build status
    :target: https://github.com/openshift-psap/topsail/actions/workflows/check_generated_ansible.yml
.. |render_docs| image:: https://github.com/openshift-psap/topsail/actions/workflows/build_docs.yml/badge.svg?event=schedule
    :alt: Render docs build status
    :target: https://github.com/openshift-psap/topsail/actions/workflows/build_docs.yml
.. |nbsp| unicode:: 0xA0 
   :trim:
