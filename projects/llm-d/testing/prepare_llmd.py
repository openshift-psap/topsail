#!/usr/bin/env python

import pathlib
import logging
import datetime
import time
import uuid
import os
import json

import yaml
import tempfile

from projects.core.library import env, config, run

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))

def update_rhoai_pull_secret(secret_file_path):
    """
    Updates the cluster pull secret with RHOAI registry credentials
    """

    # Read secret from file
    secret = secret_file_path.read_text().strip()
    if not secret:
        raise ValueError(f"Secret file {secret_file_path} is empty")

    logging.info("Checking current pull secret for quay.io/rhoai registry")

    # Get current pull secret
    result = run.run('oc get secret/pull-secret -n openshift-config --template="{{index .data \\".dockerconfigjson\\" | base64decode}}"', capture_stdout=True)
    current_secret = result.stdout

    # Check if registry already configured
    if "quay.io/rhoai" in current_secret:
        logging.info("Registry quay.io/rhoai already configured in pull secret")
        #return

    logging.info("Adding quay.io/rhoai registry to pull secret")

    # Create temporary file with current secret
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        temp_file.write(current_secret)
        temp_file_path = temp_file.name

    try:
        # Add registry authentication
        run.run(f'oc registry login --registry=quay.io/rhoai --auth-basic="{secret}" --to="{temp_file_path}"', log_command=False)

        # Update cluster secret
        run.run(f'oc set data secret/pull-secret -n openshift-config --from-file=.dockerconfigjson="{temp_file_path}"', log_command=False)

        logging.info("Successfully updated pull secret with quay.io/rhoai registry")
    finally:
        # Clean up temporary file
        os.unlink(temp_file_path)

def wait_for_pull_secret_ready(registry="quay.io/rhoai", test_image=None, timeout=300):
    """
    Wait for the pull secret to be deployed and working across all nodes
    """
    logging.info(f"Waiting for pull secret with {registry} to be deployed...")
    start_time = time.time()

    # Flags to track completed steps
    secret_contains_registry = False
    secret_json_valid = False
    machine_config_updated = False
    registry_access_tested = False

    while time.time() - start_time < timeout:
        try:
            # Check that the pull secret contains the registry (only if not already verified)
            if not secret_contains_registry:
                result = run.run('oc get secret/pull-secret -n openshift-config --template="{{index .data \\".dockerconfigjson\\" | base64decode}}"', capture_stdout=True)
                secret_content = result.stdout

                if registry not in secret_content:
                    logging.info(f"Pull secret does not yet contain {registry}, waiting...")
                    time.sleep(10)
                    continue
                else:
                    logging.info(f"✓ Pull secret contains {registry}")
                    secret_contains_registry = True

            # Verify the secret is properly formatted JSON (only if not already verified)
            if not secret_json_valid:
                result = run.run('oc get secret/pull-secret -n openshift-config --template="{{index .data \\".dockerconfigjson\\" | base64decode}}"', capture_stdout=True)
                secret_content = result.stdout

                try:
                    secret_data = json.loads(secret_content)
                    if "auths" not in secret_data:
                        logging.warning("Pull secret missing 'auths' section, waiting...")
                        time.sleep(10)
                        continue

                    if registry not in secret_data["auths"]:
                        logging.info(f"Registry {registry} not found in auths section, waiting...")
                        time.sleep(10)
                        continue

                    # Check that auth data exists
                    auth_data = secret_data["auths"][registry]
                    if not auth_data.get("auth") and not auth_data.get("username"):
                        logging.warning(f"Registry {registry} missing authentication data, waiting...")
                        time.sleep(10)
                        continue

                    logging.info("✓ Pull secret JSON structure valid")
                    secret_json_valid = True

                except json.JSONDecodeError:
                    logging.warning("Pull secret is not valid JSON, waiting...")
                    time.sleep(10)
                    continue

            # Check machine config pool status (only if not already updated)
            if not machine_config_updated:
                logging.info("Checking machine config propagation...")
                result = run.run("oc get mcp -o jsonpath='{.items[*].status.conditions[?(@.type==\"Updated\")].status}'", capture_stdout=True)
                if "False" in result.stdout:
                    logging.info("Machine config pools still updating, waiting...")
                    time.sleep(30)
                    continue
                else:
                    logging.info("✓ Machine config pools updated")
                    machine_config_updated = True

            # Verify nodes can access the registry using crictl (only if not already tested)
            if test_image and not registry_access_tested:
                logging.info("Validating registry access on nodes...")

                # Get a worker node to test registry access
                result = run.run("oc get nodes -l node-role.kubernetes.io/worker --no-headers -o custom-columns=NAME:.metadata.name | head -1",
                                 capture_stdout=True)
                if result.returncode == 0 and result.stdout.strip():
                    test_node = result.stdout.strip()

                    logging.info(f"Testing pull of {test_image} from node {test_node}")

                    test_result = run.run(f'oc debug node/{test_node} -- chroot /host crictl pull {test_image}',
                                          capture_stdout=True, capture_stderr=True, check=False)
                    if test_result.returncode != 0:
                        logging.warning(f"Failed to pull test image: {test_result.stderr}")
                        logging.warning("Registry access test failed, but continuing with deployment")
                        time.sleep(15)
                        continue

                    logging.info("✓ Successfully pulled test image - registry access confirmed")
                    registry_access_tested = True
                    # Clean up the pulled image
                    run.run(f'oc debug node/{test_node} -- chroot /host crictl rmi {test_image}',
                            capture_stdout=True, capture_stderr=True, check=False)
                else:
                    logging.warning("No worker nodes found for registry access testing")
                    registry_access_tested = True  # Don't retry the test

            # Check if all required steps are complete
            required_tests_complete = secret_contains_registry and secret_json_valid and machine_config_updated
            optional_test_complete = not test_image or registry_access_tested

            if required_tests_complete and optional_test_complete:
                logging.info(f"Pull secret with {registry} is ready and deployed!")
                return True

            # If we get here, some steps are still pending
            logging.info("Some validation steps still in progress, continuing to wait...")

        except Exception as e:
            logging.warning(f"Error checking pull secret status: {e}")

        time.sleep(15)

    # Timeout reached
    logging.error(f"Timeout waiting for pull secret with {registry} to be ready")
    return False


def prepare():
    """
    Prepares the cluster for LLM-D testing
    """

    if config.project.get_config("prepare.skip"):
        logging.info("Preparation skipped")
        return

    prepare_operators()
    prepare_namespace()
    prepare_monitoring()
    prepare_grafana()
    prepare_rhoai()
    prepare_gateway()
    scale_up()

    with run.Parallel("prepare_node") as parallel:
        parallel.delayed(wait_for_gpu_readiness)
        parallel.delayed(preload_llm_model_image)


def prepare_operators():
    """
    Prepares operators defined in the configuration
    """

    if config.project.get_config("prepare.operators.skip"):
        logging.info("Operators preparation skipped")
        return

    operators_list = config.project.get_config("prepare.operators.list")
    if not operators_list:
        logging.info("No operators to deploy")
        return

    logging.info("Preparing operators")

    with run.Parallel("prepare_operators") as parallel:
        for operator_config in operators_list:
            parallel.delayed(deploy_operator, operator_config)


def deploy_operator(operator_config):
    """
    Deploys a single operator based on configuration
    """

    name = operator_config.get("name")
    catalog = operator_config.get("catalog", "redhat-operators")
    operator = operator_config.get("operator")
    namespace = operator_config.get("namespace", "all")
    deploy_cr = operator_config.get("deploy_cr", False)
    enabled = operator_config.get("enabled", True)

    if not enabled:
        logging.info(f"Skipping disabled operator: {name}")
        return

    if not operator:
        logging.error(f"Operator configuration missing 'operator' field: {operator_config}")
        return

    logging.info(f"Deploying operator: {name}")

    # Build the arguments dictionary
    args_dict = {
        "catalog": catalog,
        "manifest_name": operator,
        "namespace": namespace,
        "artifact_dir_suffix": f"_{operator}"
    }

    if deploy_cr is not None:
        args_dict["deploy_cr"] = True if deploy_cr is True else \
            str(deploy_cr)

    # Add any extra arguments
    extra_args = operator_config.get("extra_args", {})
    if extra_args:
        args_dict.update(extra_args)

    run.run_toolbox("cluster", "deploy_operator", **args_dict)
    logging.info(f"Successfully deployed operator: {name}")


def prepare_grafana():
    """
    Prepares Grafana resources (datasources and dashboards)
    """

    if config.project.get_config("prepare.grafana.skip"):
        logging.info("Grafana preparation skipped")
        return

    logging.info("Preparing Grafana resources")

    # Get Grafana namespace from config
    grafana_namespace = config.project.get_config("prepare.grafana.namespace")

    # Create Grafana namespace if it doesn't exist
    logging.info(f"Creating Grafana namespace: {grafana_namespace}")
    run.run(f'oc new-project "{grafana_namespace}" --skip-config-write >/dev/null', check=False)

    # Deploy Grafana datasources
    datasources = config.project.get_config("prepare.grafana.datasources")
    for datasource_path in datasources or []:
        datasource_file = TESTING_THIS_DIR / datasource_path
        if not datasource_file.exists():
            logging.warning(f"Grafana datasource file not found: {datasource_file}")
            continue

        logging.info(f"Deploying Grafana datasource: {datasource_path} to namespace {grafana_namespace}")
        run.run(f"oc apply -n {grafana_namespace} -f {datasource_file}")

    # Deploy Grafana dashboards
    dashboards_dir_path = config.project.get_config("prepare.grafana.dashboards_dir")
    if dashboards_dir_path:
        dashboards_dir = TESTING_THIS_DIR / dashboards_dir_path
        dashboard_files = list(dashboards_dir.glob("*.yaml"))
        logging.info(f"Deploying {len(dashboard_files)} Grafana dashboard(s) from {dashboards_dir_path} to namespace {grafana_namespace}")
        for dashboard_file in dashboard_files:
            logging.info(f"  - {dashboard_file.name}")
            run.run(f"oc apply -n {grafana_namespace} -f {dashboard_file}")
    else:
        logging.info("No Grafana dashboards directory configured")


def prepare_monitoring():
    """
    Prepares cluster monitoring (user workload monitoring)
    """

    if config.project.get_config("prepare.monitoring.skip"):
        logging.info("Monitoring preparation skipped")
        return

    logging.info("Preparing cluster monitoring")

    # Get namespaces to enable monitoring for
    monitored_namespaces = config.project.get_config("prepare.monitoring.namespaces")
    for i, ns in enumerate(monitored_namespaces):
        # we fetch the *list*, so the references aren't resolved in 'get_config',
        # eg: ['@prepare.namespace.name']
        monitored_namespaces[i] = config.project.resolve_reference(ns)

    # Enable user workload monitoring
    run.run_toolbox("cluster", "enable_userworkload_monitoring",
                    namespaces=monitored_namespaces or [])

    logging.info("Cluster monitoring setup completed successfully")


def scale_up():
    """
    Prepares the cluster for GPU operations - scales up unconditionally if configured
    """

    logging.info("Scaling up the cluster")

    # Scale up the cluster if configured
    node_instance_type = config.project.get_config("prepare.cluster.nodes.instance_type")
    node_count = config.project.get_config("prepare.cluster.nodes.count")

    if node_instance_type and node_count:
        logging.info(f"Scaling cluster to {node_count} {node_instance_type} instances")
        run.run_toolbox("cluster", "set_scale",
                       instance_type=node_instance_type,
                       scale=node_count)

def wait_for_gpu_readiness():
    """
    Waits for GPU nodes and GPU operator stack to be ready
    """
    logging.info("Waiting for GPU nodes to be ready...")
    run.run_toolbox("nfd", "wait_gpu_nodes")
    run.run_toolbox("gpu-operator", "wait_stack_deployed")
    logging.info("GPU readiness check completed")


def prepare_rhoai():
    """
    Prepares RHOAI (Red Hat OpenShift AI)
    """

    if config.project.get_config("prepare.rhoai.skip"):
        logging.info("RHOAI preparation skipped")
        return

    logging.info("Preparing RHOAI")

    # Apply pre-release registry token if available

    rhoai_secret_file = PSAP_ODS_SECRET_PATH / config.project.get_config("secrets.rhoai_rc")
    if rhoai_secret_file.exists():
        logging.info("Applying pre-release image registry token")
        update_rhoai_pull_secret(rhoai_secret_file)

        # Wait for the pull secret to be deployed and working
        rhoai_image = config.project.get_config("prepare.rhoai.image")
        rhoai_tag = config.project.get_config("prepare.rhoai.tag")
        test_image = f"{rhoai_image}:{rhoai_tag}"

        if not wait_for_pull_secret_ready("quay.io/rhoai", test_image=test_image):
            raise RuntimeError("Pull secret deployment failed or timed out")
    else:
        logging.error(f"RHOAI secret file not found: {rhoai_secret_file}")

    # Apply ImageContentSourcePolicy for quay registry
    icsp_yaml = """
apiVersion: operator.openshift.io/v1alpha1
kind: ImageContentSourcePolicy
metadata:
  name: quay-registry
spec:
  repositoryDigestMirrors:
    - source: registry.redhat.io/rhoai
      mirrors:
        - quay.io/rhoai
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(icsp_yaml)
        temp_file = f.name

    run.run(f"oc apply -f {temp_file}")

    # Deploy RHOAI
    rhoai_image = config.project.get_config("prepare.rhoai.image")
    rhoai_tag = config.project.get_config("prepare.rhoai.tag")
    rhoai_channel = config.project.get_config("prepare.rhoai.channel")

    run.run_toolbox("rhods", "deploy_ods",
                    catalog_image=rhoai_image,
                    tag=rhoai_tag,
                    channel=rhoai_channel)

    # Enable KServe
    enable_components = config.project.get_config("prepare.rhoai.datasciencecluster.enable")
    extra_settings = config.project.get_config("prepare.rhoai.datasciencecluster.extra_settings")

    run.run_toolbox("rhods", "update_datasciencecluster",
                   enable=enable_components,
                   extra_settings=extra_settings)


def prepare_gateway():
    """
    Prepares the Gateway for LLM inference
    """

    if config.project.get_config("prepare.gateway.skip"):
        logging.info("Gateway preparation skipped")
        return

    logging.info("Preparing Gateway for LLM inference")

    # Get gateway name from config
    gateway_name = config.project.get_config("prepare.gateway.name")

    logging.info(f"Deploying gateway: {gateway_name}")

    run.run_toolbox("llmd", "deploy_gateway", name=gateway_name)


def prepare_namespace():
    """
    Prepares the namespace for LLM testing
    """

    namespace = config.project.get_config("prepare.namespace.name")

    logging.info(f"Preparing namespace: {namespace}")

    # Create the namespace
    run.run(f'oc new-project "{namespace}" --skip-config-write >/dev/null', check=False)

    return namespace


def cleanup_cluster():
    """
    Cleans up the cluster
    """

    if config.project.get_config("prepare.cleanup.skip"):
        logging.info("Cleanup skipped")
        return

    logging.info("Cleaning up LLM-D cluster resources")

    namespace = config.project.get_config("prepare.namespace.name")

    # Delete namespace
    try:
        run.run(f"oc delete namespace {namespace} --ignore-not-found")
    except Exception as e:
        logging.warning(f"Failed to delete namespace {namespace}: {e}")

    # Scale down cluster if configured
    auto_scale_down = config.project.get_config("prepare.cluster.nodes.auto_scale_down_on_exit")
    node_instance_type = config.project.get_config("prepare.cluster.nodes.instance_type")

    if auto_scale_down and node_instance_type:
        logging.info(f"Auto scale down enabled, scaling down {node_instance_type} nodes to 0")
        run.run_toolbox("cluster", "set_scale",
                        instance_type=node_instance_type,
                        scale="0")

def preload_llm_model_image():
    """
    Preloads the LLM model image on GPU nodes to reduce startup time
    """

    logging.info("Preloading LLM model image on GPU nodes")

    try:
        all_images = {}
        # Get the model image URI from the YAML file
        llmisvc_file = config.project.get_config("tests.llmd.inference_service.yaml_file")
        yaml_file = TESTING_THIS_DIR / "llmisvcs" / llmisvc_file
        namespace = config.project.get_config("tests.llmd.namespace")

        # Extract the model URI using yq
        image_result = run.run(f"cat {yaml_file} | yq .spec.model.uri", capture_stdout=True)

        if image_result.returncode != 0:
            raise RuntimeError(f"Failed to extract model URI from {yaml_file}: {image_result.stderr}")

        model_image = image_result.stdout.strip().strip('"').strip("oci://")
        image_name = run.run(f"cat {yaml_file} | yq .spec.model.name", capture_stdout=True).stdout.strip().strip('"')
        logging.info(f"Preloading model image: {model_image} ({image_name})")
        all_images[image_name] = model_image

        # Get additional images from RHODS operator CSV
        logging.info("Fetching additional images from RHODS operator CSV")

        # First get the actual CSV name
        csv_name_result = run.run("oc get csv -n redhat-ods-operator -l operators.coreos.com/rhods-operator.redhat-ods-operator -oname", capture_stdout=True)

        if csv_name_result.returncode != 0:
            logging.warning(f"Failed to get RHODS operator CSV name: {csv_name_result.stderr}")
            additional_images = []
        else:
            csv_name = csv_name_result.stdout.strip().replace("clusterserviceversion.operators.coreos.com/", "")
            logging.info(f"Found RHODS operator CSV: {csv_name}")

            csv_result = run.run(f"oc get csv {csv_name} -n redhat-ods-operator -ojson | jq '.spec.relatedImages'", capture_stdout=True)

            if csv_result.returncode != 0:
                logging.warning(f"Failed to get RHODS operator related images (return code: {csv_result.returncode}): {csv_result.stderr}")
                additional_images = []
            else:
                # Parse the JSON output to get specific images
                related_images = json.loads(csv_result.stdout)

                # Extract the specific images we need
                target_image_names = [
                    "rhaiis_vllm_cuda_image",
                    "odh_llm_d_inference_scheduler_image",
                    "odh_llm_d_routing_sidecar_image"
                ]

                logging.info(f"Parsed {len(related_images)} related images from CSV")

                additional_images = []

                for i, img in enumerate(related_images):
                    img_name = img["name"]
                    if img_name not in target_image_names:
                        continue
                    all_images[img_name] = img["image"]
                    logging.info(f"Found additional image to preload: {img_name} = {img['image']}")

                logging.info(f"Found {len(additional_images)} additional images to preload out of {len(target_image_names)} targets")

        # Preload all images in parallel
        logging.info(f"Starting parallel preload of {len(all_images)} images")

        with run.Parallel("preload_images") as parallel:
            for image_name, image in all_images.items():
                parallel.delayed(preload_single_image, namespace, image, image_name)

        logging.info("LLM model and related images preloading completed successfully")

    except Exception as e:
        logging.error(f"Failed to preload LLM model image: {e}")
        raise


def preload_single_image(namespace, image, image_name=""):
    """
    Preloads a single image on GPU nodes
    """
    try:
        logging.info(f"Preloading image{f' {image_name}' if image_name else ''}: {image}")
        run.run_toolbox("cluster", "preload_image",
                        name=image_name or "preload",
                        namespace=namespace,
                        node_selector_key="nvidia.com/gpu.present",
                        node_selector_value="true",
                        image=image)
    except Exception as e:
        logging.error(f"Failed to preload image{f' {image_name}' if image_name else ''} {image}: {e}")
        raise
