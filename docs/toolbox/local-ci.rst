==================
Local CI Execution
==================

Deployment
==========

* Build the image used for the Prow CI testing, and run a given command in the Pod

.. code-block:: shell

    toolbox/local-ci/deploy.sh                 \
              <ci command>                     \
              <git repository> <git reference> \
              [gpu_operator_image_tag_uid]

**Example:**

.. code-block:: shell

    toolbox/local-ci/deploy.sh                        \
                "run gpu-operator test_master_branch" \
                https://github.com/openshift-psap/ci-artifacts.git master

Cleaning Up
===========

* Cleanup the resources used to deploy the test image

.. code-block:: shell

    toolbox/local-ci/cleanup.sh
