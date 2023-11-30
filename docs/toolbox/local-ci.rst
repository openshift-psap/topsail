==================
Local CI Execution
==================

Deployment
==========

Requirements:

- When running `local-ci` you need to define the `ARTIFACTS_DIR` ENV variable manually

* Build the image used for the Prow CI testing, and run a given command in the Pod

.. code-block:: shell

    ./run_toolbox.py local-ci deploy                   \
              <ci command>                     \
              <git repository> <git reference> \
              [--tag_uid=TAG_UID]

**Example:**

.. code-block:: shell

    ./run_toolbox.py local-ci deploy                          \
             "run gpu-operator test_master_branch" \
             https://github.com/openshift-psap/ci-artifacts.git master

Cleaning Up
===========

* Cleanup the resources used to deploy the test image

.. code-block:: shell

    ./run_toolbox.py local-ci cleanup

Deploying the RHODS stack  from a container
===========================================

* Cleanup the resources used to deploy the test image

.. code-block:: shell

    # Configure the ods secrets file
    mkdir -p ~/ods_secrets
    touch ~/ods_secrets/brew.registry.redhat.io.token
    echo "f...A==" > ~/ods_secrets/brew.registry.redhat.io.token
    # Configure the kubeconfig file
    touch ~/.kubeconfig
    echo "the kubeconfig file content" > ~/.kubeconfig
    # Create a local tmp folder to store the logs
    mkdir -p ~/topsail_tmp
    chmod 777 ~/topsail_tmp
    # Get topsail
    git clone https://github.com/openshift-psap/topsail
    cd topsail
    docker build -t topsail/topsail .

    # Debugging file structure
    # docker run -it --entrypoint /bin/bash  topsail/topsail

    # Requirements:
    # Make sure that from the container you are able to reach the cluster's API endpoints.
    # Make sure the Kubeconfig file is mounted correctly.
    # Make sure the ODS secrets folder is mounted correctly.
    # Make sure the example tmp folder exists to write logs
    docker run \
    -e PSAP_ODS_SECRET_PATH=/home/topsail/ods_secrets \
    -v ~/ods_secrets:/home/topsail/ods_secrets \
    -e KUBECONFIG=/home/topsail/.kubeconfig \
    -v ~/.kubeconfig:/home/topsail/.kubeconfig \
    -v ~/topsail_tmp:/tmp:z \
    --add-host api.p40.example.com:10.19.96.54 \
    --add-host oauth-openshift.apps.p40.example.com:10.19.96.54 \
    --add-host console-openshift-console.apps.p40.example.com:10.19.96.54 \
    --add-host grafana-openshift-monitoring.apps.p40.example.com:10.19.96.54 \
    --add-host thanos-querier-openshift-monitoring.apps.p40.example.com:10.19.96.54 \
    --add-host prometheus-k8s-openshift-monitoring.apps.p40.example.com:10.19.96.54 \
    --add-host alertmanager-main-openshift-monitoring.apps.p40.example.com:10.19.96.54 \
    --name topsail topsail/topsail \
    ./projects/skeleton/testing/test.py test_ci