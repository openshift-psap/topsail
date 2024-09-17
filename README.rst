TOPSAIL
=======

Red Hat/PSAP's Test Orchestrator for Performance and Scalability of AI
pLatforms

|lint| |nbsp| |consistency| |nbsp| |render_ansible| |nbsp| |render_docs|

This repository provides an extensive toolbox for performance and
scale testing of `Red Hat OpenShift
AI <https://www.redhat.com/en/technologies/cloud-computing/openshift/openshift-ai>`_
(RHOAI) platform.

The automation relies on:

- Python scripts for the orchestration (the ``testing`` directories)
- Ansible roles for the cluster control (the ``toolbox`` and ``roles``
  directories)
- `MatrixBenchmarking
  <https://github.com/openshift-psap/matrix-benchmarking>`_ for the
  post-processing (the ``visualization`` directories)

Dependencies
------------

The recommended way to run TOPSAIL either via a CI environment, or
within TOPSAIL container via its `Toolbx
<https://containertoolbx.org/>`_ `launcher
<https://github.com/openshift-psap/topsail/tree/main/launcher>`_.

Requirements:

- All the software requirements should be provided by the container
  image, built by the ``topsail_build`` command.


- A reachable OpenShift cluster

.. code-block:: shell

    oc version # fails if the cluster is not reachable

Note that TOPSAIL assumes that it has cluster-admin privileges to the
cluster.

TOPSAIL orchestration and toolbox
---------------------------------

TOPSAIL provides multiple levels of functionalities:

1. the test orchestrations are top level. Most of the time, they are
   triggered via a CI engine, for end-to-end testing of a given RHOAI
   component. The test orchestration Python code and configuration is
   stored in the ``projects/*/testing`` directory.
2. the toolbox commands operate between the orchestration code and the
   cluster. They are Ansible roles (``projects/*/toolbox``), in charge
   of a specific task to prepare the cluster, run a given test,
   capture the state of the cluster ... The Ansible roles have a thin
   Python layer on top of them (based on the `Google Fire
   <https://github.com/google/python-fire>`_ package) which provides a
   well-defined command-line interface (CLI). This CLI interface
   documents the parameters of the command, it allows its discovery
   via the `./run_toolbox.py` entrypoint, and it generates artifacts
   for post-mortem troubleshooting.
3. the post-processing visualization, provided via `MatrixBenchmarking
   <https://github.com/openshift-psap/matrix-benchmarking>`_ workload
   modules (``projects/*/visualization``). The modules are in charge of
   parsing the test artifacts, generating visualization reports,
   uploading KPIs to OpenSearch, and performing regression analyses.

TOPSAIL ``projects`` organization
---------------------------------

TOPSAIL `projects
<https://github.com/openshift-psap/topsail/tree/main/projects>`_
directories are organized following the different levels described
above.

* the ``testing`` directory provides the Python scripts with CI
  entrypoints (``test.py prepare_ci`` and ``test.py run_ci``) and possibly
  extra entrypoints for local interactions. It also contains the
  project configuration file (``config.yaml``)
* the ``toolbox`` directory contains the Ansible roles that controls and
  mutates the cluster during the cluster preparation and test
* the ``toolbox`` directory also contains the Python wrapper which
  provides a well-defined CLI over the Ansible roles
* the ``visualization`` directory contains the MatrixBenchmarking
  workload modules, which perform the post-processing step of the test
  (parsing, visualization, regression analyze)


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
