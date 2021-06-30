============
Introduction
============

As part of Red Hat PSAP team, we run nightly a set of tests to
validate the proper execution of the operators we are in charge of:

- the `GPU Operator <https://openshift-psap.github.io/ci-dashboard/gpu-operator_daily-matrix.html>`_
- the `Node Feature Discovery operator <https://openshift-psap.github.io/ci-dashboard/nfd_daily-matrix.html>`_
- the `Node Tuning Operator <https://openshift-psap.github.io/ci-dashboard/nto_daily-matrix.html>`_
- the `Special Resource Operator <https://openshift-psap.github.io/ci-dashboard/sro_daily-matrix.html>`_

The execution of these nightly tests is controlled by the code in the
`ci-artifacts <https://github.com/openshift-psap/ci-artifacts/>`_
repository, and the test steps are driven by the `toolbox
<https://openshift-psap.github.io/ci-artifacts/index.html#psap-toolbox>`_
commands.

The nightly test overview is generated with the help of the `ci-dashboard
<https://github.com/openshift-psap/ci-dashboard/>`_ repository.
