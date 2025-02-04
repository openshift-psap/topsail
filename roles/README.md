TOPSAIL Projects
================

This directory contains TOPSAIL roles.

A project hosts the perf/scale testing code related to a given RHOAI
component, or provides reusable functionalities useful for multiple
tests.

# Notable reusable projects

* `cluster`: a large set of generic commands for preparing the
  cluster

* `rhods`: commands related to RHOAI (new name of RHODS) deployment
  and control

* `gpu_operator` and `nfd_operator`: commands related to the
  deployment of the GPU Operator (required component to run GPU
  workload on OpenShift)

* `local_ci`: commands for running like in a CI engine ... without a
  CI engine. And for running multiple TOPSAIL users in parallel (for
    multi-user scale testing)

* `llm_load_test`: commands for launching PSAP's `llm-load-test
  <https://github.com/openshift-psap/llm-load-test>`_ inference server
  performance tests

* `skeleton`: sample project that can be duplicated to build a new
  perf&scale project

# Notable perf & scale projects

* `kserve`: project used for in-depth performance testing and
  investions of RHOAI KServe model-serving
* `fine-tuning`: project used for in-depth performance testing and
  investigations of RHOAI Kubeflow-training operator -based fine-tuning
* `pipelines`: project used for in-depth scale testing and
  investigations of RHOAI DataScience Pipelines
* `notebooks`: project used for in-depth scale testing and
  investigations of RHOAI Dashboard & Workbenches
