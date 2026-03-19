#!/usr/bin/env python

import pathlib
import logging
import datetime
import time
import uuid
import os
import json

import yaml

from projects.core.library import env, config, run
from projects.cluster.library import prom
from projects.matrix_benchmarking.library import visualize
import prepare_llmd

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent

def test_single_flavor(flavor, flavor_index, total_flavors, namespace):
    """
    Run tests for a single flavor

    Args:
        flavor: The flavor string to test
        flavor_index: Current flavor number (1-indexed)
        total_flavors: Total number of flavors being tested
        namespace: Kubernetes namespace to use

    Returns:
        False if test succeeded, Exception or True if test failed
    """
    logging.info(f"Running test for flavor: {flavor} ({flavor_index}/{total_flavors})")

    flavor_failed = False
    prom_start_ts = None

    llmisvc_name = config.project.get_config("tests.llmd.inference_service.name")
    llmisvc_name += f"-{flavor}"

    with env.NextArtifactDir(f"flavor_{flavor}"):
        try:
            # Clean up any existing LLM inference services and pods before testing
            if not config.project.get_config("tests.llmd.inference_service.skip_deployment"):
                cleanup_llm_inference_resources()

            # Reset Prometheus before testing
            if config.project.get_config("tests.capture_prom"):
                logging.info("Resetting Prometheus database before testing")
                prom_start_ts = prom.reset_prometheus()

            # Deploy LLM inference service
            _, _, llmisvc_path = deploy_llm_inference_service(flavor, llmisvc_name, namespace)

            # Extract the model name from configuration
            model_ref = config.project.get_config("tests.llmd.inference_service.model")

            models = config.project.get_config(f"models")
            model_name = models[model_ref]["name"]
            logging.info(f"Using model: {model_name} (from config reference: {model_ref})")

            # Get the service URL
            endpoint_url = get_llm_inference_url(llmisvc_name, namespace, flavor)

            if config.project.get_config("tests.llmd.inference_service.do_simple_test"):
                if not test_llm_inference_simple(endpoint_url, llmisvc_name, namespace, model_name):
                    raise RuntimeError("Simple inference test failed :/")

            # Run benchmarks
            if config.project.get_config("tests.llmd.benchmarks.multiturn.enabled"):
                flavor_failed |= run_multiturn_benchmark(endpoint_url, llmisvc_name, namespace)

            if config.project.get_config("tests.llmd.benchmarks.guidellm.enabled"):
                flavor_failed |= run_guidellm_benchmark(endpoint_url, llmisvc_name, namespace)

        except Exception as e:
            logging.exception(f"Test failed for flavor {flavor} :/")
            flavor_failed = e

        finally:
            # Always capture LLM inference service state (success or failure)
            logging.info("Capturing LLM inference service state for debugging")
            try:
                capture_llm_inference_service_state(llmisvc_name, namespace)
            except Exception as capture_e:
                logging.warning(f"Failed to capture LLM inference service state: {capture_e}")

            # Always dump Prometheus data after testing (success or failure)
            logging.info("Dumping Prometheus database after testing")
            namespace = config.project.get_config("tests.llmd.namespace")
            if prom_start_ts:
                prom.dump_prometheus(prom_start_ts, namespace)

            # Clean up LLM inference service resources after this flavor
            logging.info(f"Cleaning up LLM inference service resources for flavor {flavor}")
            try:
                cleanup_llm_inference_resources()
            except Exception as cleanup_e:
                logging.warning(f"Failed to cleanup LLM inference service resources: {cleanup_e}")

        # Generate test metadata files for this flavor
        _generate_test_metadata(flavor_failed, flavor)

        return flavor_failed


def test():
    """
    Runs the main LLM-D test
    """

    if config.project.get_config("tests.llmd.skip"):
        logging.info("LLM-D test skipped")
        return False

    logging.info("Running LLM-D test")

    # Get test flavors from config
    flavors = config.project.get_config("tests.llmd.flavors")
    if not isinstance(flavors, list):
        flavors = [flavors]

    if config.project.get_config("tests.llmd.inference_service.skip_deployment"):
        if len(flavors) != 1:
            raise ValueError("tests.llmd.inference_service.skip_deployment is set "
                             f"but got multiple flavors to deploy: {', '.join(flavors)}")

    if not config.project.get_config("tests.llmd.skip_prepare"):
        prepare_for_test()
    else:
        logging.info("Skipping test preparation (tests.llmd.skip_prepare=True)")

    logging.info(f"Running tests for flavors: {flavors}")

    overall_failed = False
    test_directory = None
    namespace = config.project.get_config("tests.llmd.namespace")

    with env.NextArtifactDir("llm_d_testing"):
        test_directory = env.ARTIFACT_DIR

        for i, flavor in enumerate(flavors):
            flavor_failed = test_single_flavor(flavor, i + 1, len(flavors), namespace)

            if flavor_failed:
                overall_failed = True
                logging.error(f"Test failed for flavor: {flavor}")
            else:
                logging.info(f"Test completed successfully for flavor: {flavor}")

    # Final cleanup of all LLM inference service resources after all flavors complete
    logging.info("Final cleanup of all LLM inference service resources")
    try:
        cleanup_llm_inference_resources()
    except Exception as cleanup_e:
        logging.warning(f"Failed to perform final cleanup of LLM inference service resources: {cleanup_e}")

    # Handle conditional GPU scaling after all tests complete
    conditional_scale_down()

    # Generate visualization if enabled
    if not config.project.get_config("tests.visualize"):
        logging.info("Visualization disabled.")
    else:
        exc = generate_visualization(test_directory, overall_failed)

        if exc:
            logging.error(f"Test visualization failed: {exc}")

        if exc and not overall_failed:
            raise exc

    if overall_failed and isinstance(overall_failed, Exception):
        raise overall_failed

    return overall_failed


def prepare_for_test():
    # Handle conditional GPU scaling before test
    conditional_scale_up()

    # Ensure GPU nodes are available before running test
    ensure_gpu_nodes_available()
    # Run GPU readiness check and image preloading in parallel
    logging.info("Starting parallel GPU readiness check and image/model preloading")

    model_ref = config.project.get_config("tests.llmd.inference_service.model")

    with run.Parallel("prepare_gpu_node") as parallel:
        parallel.delayed(prepare_llmd.wait_for_gpu_readiness)
        parallel.delayed(prepare_llmd.preload_llm_model_image)
        parallel.delayed(prepare_llmd.download_single_model, model_ref)

def _generate_test_metadata(failed, flavor):
    """
    Generate metadata files for the test execution
    """
    logging.info(f"Generating test metadata files for flavor: {flavor}")

    # Write exit code file
    exit_code = "1" if failed else "0"
    exit_code_path = env.ARTIFACT_DIR / "exit_code"
    with open(exit_code_path, 'w') as f:
        f.write(exit_code)

    logging.info(f"Written exit code: {exit_code} to {exit_code_path}")

    # Write settings file using YAML
    settings_path = env.ARTIFACT_DIR / "settings.yaml"
    settings_data = {
        "llm-d": True,
        "flavor": flavor
    }

    with open(settings_path, 'w') as f:
        yaml.dump(settings_data, f, default_flow_style=False)

    logging.info(f"Written settings to {settings_path} for flavor: {flavor}")


def generate_visualization(test_artifact_dir, test_failed):
    """
    Generate visualization from test artifacts
    """
    exc = None

    with env.NextArtifactDir("plots"):
        exc = run.run_and_catch(
            exc,
            visualize.generate_from_dir,
            test_artifact_dir,
            test_failed=test_failed
        )
        if not exc:
            logging.info(f"Test visualization has been generated into {env.ARTIFACT_DIR}/reports_index.html")
        else:
            logging.info(f"Test failed. See '{env.ARTIFACT_DIR}' for more details. {exc}")

    return exc


def parse_flavor_components(flavor):
    """
    Parse flavor string into components dictionary

    Examples:
    - 'intelligentrouting-tp2-x2' -> {'base': 'intelligentrouting', 'tp_size': 2, 'replicas': 2}
    - 'simple' -> {'base': 'simple', 'tp_size': None, 'replicas': None}
    - 'intelligentrouting-x2' -> {'base': 'intelligentrouting', 'tp_size': None, 'replicas': 2}
    - 'intelligentrouting' -> {'base': 'intelligentrouting', 'tp_size': None, 'replicas': None}

    Args:
        flavor: The flavor string to parse

    Returns:
        dict: {'base': str, 'tp_size': int|None, 'replicas': int|None}
    """
    parts = flavor.split('-')
    components = {
        'base': parts[0],
        'tp_size': None,
        'replicas': None
    }

    # Parse remaining parts
    for part in parts[1:]:
        if part.startswith('tp') and len(part) > 2:
            try:
                components['tp_size'] = int(part[2:])
            except ValueError:
                raise ValueError(f"Invalid TP specification: {part}. Expected format: tp<number> (e.g., tp2, tp8)")
        elif part.startswith('x') and len(part) > 1:
            try:
                components['replicas'] = int(part[1:])
            except ValueError:
                raise ValueError(f"Invalid replica specification: {part}. Expected format: x<number> (e.g., x2, x4)")
        else:
            raise ValueError(f"Unknown flavor component: {part}. Expected format: <base>-[tp<number>]-[x<number>] (e.g., simple-tp8-x2)")

    logging.info(f"Parsed flavor '{flavor}' -> {components}")
    return components


def apply_flavor_modifications(isvc_data, flavor):
    """
    Apply flavor-specific modifications to the ISVC data

    Args:
        isvc_data: The loaded YAML data structure
        flavor: The flavor string to apply
    """
    logging.info(f"Applying flavor modifications for: {flavor}")

    # Parse the flavor components
    components = parse_flavor_components(flavor)
    base_flavor = components['base']
    tp_size = components['tp_size']
    replicas = components['replicas']

    # Apply base flavor modifications
    if base_flavor == "simple":
        logging.info("Applying 'simple' flavor modifications")
        # Remove spec.router if it exists
        if 'router' in isvc_data.get('spec', {}):
            del isvc_data['spec']['router']
            logging.info("Removed spec.router for 'simple' flavor")

    elif base_flavor in ["intelligentrouting", "intelligent-routing"]:
        logging.info("Applying 'intelligent-routing' flavor - keeping ISVC untouched")
        # No modifications - keep original ISVC configuration

    elif base_flavor == "default":
        logging.info("Applying 'default' flavor - keeping ISVC untouched")
        # No modifications - keep original ISVC configuration

    else:
        # Unknown flavor
        raise ValueError(f"Unknown base flavor '{base_flavor}'. Supported flavors: simple, intelligentrouting")

    # Ensure spec section exists
    if 'spec' not in isvc_data:
        isvc_data['spec'] = {}

    # Apply replica scaling from flavor
    if replicas is not None:
        isvc_data['spec']['replicas'] = replicas
        logging.info(f"Setting spec.replicas = {replicas}")

    # Apply tensor parallelism from flavor
    if tp_size is not None:
        apply_flavor_tensor_parallelism(isvc_data, tp_size)


def apply_flavor_tensor_parallelism(isvc_data, tp_size):
    """
    Apply tensor parallelism configuration from flavor to the ISVC

    Args:
        isvc_data: The loaded YAML data structure
        tp_size: Tensor parallel size from flavor
    """
    logging.info(f"Applying tensor parallelism from flavor: TP={tp_size}")

    # Ensure template.containers section exists
    if 'template' not in isvc_data['spec']:
        isvc_data['spec']['template'] = {}
    if 'containers' not in isvc_data['spec']['template']:
        isvc_data['spec']['template']['containers'] = [{'name': 'main'}]

    # Find the main container
    main_container = None
    for container in isvc_data['spec']['template']['containers']:
        if container.get('name') == 'main':
            main_container = container
            break

    if not main_container:
        main_container = {'name': 'main'}
        isvc_data['spec']['template']['containers'].append(main_container)

    # Ensure env section exists
    if 'env' not in main_container:
        main_container['env'] = []

    # Find or create VLLM_ADDITIONAL_ARGS environment variable
    vllm_args_env = None
    for env_var in main_container['env']:
        if env_var.get('name') == 'VLLM_ADDITIONAL_ARGS':
            vllm_args_env = env_var
            break

    if not vllm_args_env:
        vllm_args_env = {'name': 'VLLM_ADDITIONAL_ARGS', 'value': ''}
        main_container['env'].append(vllm_args_env)

    # Add tensor parallelism argument
    current_args = vllm_args_env.get('value', '').strip()
    tp_arg = f"--tensor-parallel-size={tp_size}"

    # Check if TP argument already exists and update it
    import re
    if re.search(r'--tensor-parallel-size=\d+', current_args):
        # Replace existing TP argument
        current_args = re.sub(r'--tensor-parallel-size=\d+', tp_arg, current_args)
    else:
        # Add new TP argument
        if current_args:
            current_args = f"{current_args} {tp_arg}"
        else:
            current_args = tp_arg

    vllm_args_env['value'] = current_args

    # Set GPU resources to match tensor parallel size
    apply_gpu_resources(main_container, tp_size)

    logging.info(f"Applied flavor TP: {tp_arg}, GPU resources: {tp_size}")


def apply_kueue_configuration(isvc_data):
    """
    Apply Kueue annotations and labels to the ISVC data

    Args:
        isvc_data: The loaded YAML data structure
    """
    kueue_config = config.project.get_config("tests.llmd.inference_service.kueue", {})

    if not kueue_config.get("enabled", False):
        logging.info("Kueue integration disabled - skipping kueue configuration")
        return

    logging.info("Applying Kueue configuration to ISVC")

    # Get prefix for kueue labels/annotations
    kueue_prefix = kueue_config.get("prefix")

    # Ensure metadata sections exist
    if 'metadata' not in isvc_data:
        isvc_data['metadata'] = {}
    if 'labels' not in isvc_data['metadata']:
        isvc_data['metadata']['labels'] = {}
    if 'annotations' not in isvc_data['metadata']:
        isvc_data['metadata']['annotations'] = {}

    # Apply Kueue labels
    kueue_labels = kueue_config.get("labels", {})
    for label_key, label_value in kueue_labels.items():
        full_label_key = f"{kueue_prefix}{label_key}"
        isvc_data['metadata']['labels'][full_label_key] = label_value
        logging.info(f"Added Kueue label: {full_label_key}={label_value}")

    # Apply Kueue annotations
    kueue_annotations = kueue_config.get("annotations", {})
    for annotation_key, annotation_value in kueue_annotations.items():
        full_annotation_key = f"{kueue_prefix}{annotation_key}"
        isvc_data['metadata']['annotations'][full_annotation_key] = annotation_value
        logging.info(f"Added Kueue annotation: {full_annotation_key}={annotation_value}")

    # Apply Kueue annotations to router scheduler pod template
    if 'spec' in isvc_data and 'router' in isvc_data['spec'] and 'scheduler' in isvc_data['spec']['router']:
        scheduler_template = isvc_data['spec']['router']['scheduler'].get('template', {})

        # Ensure metadata exists in scheduler template
        if 'metadata' not in scheduler_template:
            scheduler_template['metadata'] = {}
        if 'annotations' not in scheduler_template['metadata']:
            scheduler_template['metadata']['annotations'] = {}

        # Apply the same Kueue annotations to the scheduler pod template
        for annotation_key, annotation_value in kueue_annotations.items():
            full_annotation_key = f"{kueue_prefix}{annotation_key}"
            scheduler_template['metadata']['annotations'][full_annotation_key] = annotation_value
            logging.info(f"Added Kueue annotation to scheduler template: {full_annotation_key}={annotation_value}")

        # Update the scheduler template back to the data structure
        isvc_data['spec']['router']['scheduler']['template'] = scheduler_template

    # Calculate pod group total count: 1 scheduler + number of replicas
    replicas = isvc_data.get('spec', {}).get('replicas', 1)
    pod_group_total_count = 1 + replicas  # 1 scheduler + replicas
    isvc_data['metadata']['annotations'][f"{kueue_prefix}pod-group-total-count"] = str(pod_group_total_count)
    logging.info(f"Set pod-group-total-count: {pod_group_total_count} (1 scheduler + {replicas} replicas)")

def apply_model_configuration(isvc_data):
    """
    Apply model URI and name configuration from config file

    Args:
        isvc_data: The loaded YAML data structure
    """
    model_key = config.project.get_config("tests.llmd.inference_service.model", None)

    if not model_key:
        logging.info("No model configuration found - using defaults from YAML")
        return

    logging.info(f"Applying model configuration for model reference: {model_key}")

    # Get model details from models section
    models_config = config.project.get_config("models", {})
    if model_key not in models_config:
        raise ValueError(f"Model '{model_key}' not found in models configuration")

    model_config = models_config[model_key]

    # Ensure spec.model section exists
    if 'spec' not in isvc_data:
        isvc_data['spec'] = {}
    if 'model' not in isvc_data['spec']:
        isvc_data['spec']['model'] = {}

    # Apply model URI if configured
    if 'uri' in model_config:
        isvc_data['spec']['model']['uri'] = model_config['uri']
        logging.info(f"Set model URI: {model_config['uri']}")
    else:
        # Construct PVC URI: pvc://<pvc_name>/<model_key>
        pvc_name = config.project.get_config("prepare.pvc.name")
        uri = f"pvc://{pvc_name}/{model_key}"
        isvc_data['spec']['model']['uri'] = uri
        logging.info(f"Set model URI: {uri}")

    # Apply model name if configured
    if 'name' in model_config:
        isvc_data['spec']['model']['name'] = model_config['name']
        logging.info(f"Set model name: {model_config['name']}")



def apply_vllm_args_configuration(isvc_data):
    """
    Apply vLLM arguments configuration (always applied)

    Args:
        isvc_data: The loaded YAML data structure
    """
    vllm_args = config.project.get_config("tests.llmd.inference_service.vllm_args", [])

    if not vllm_args:
        logging.info("No vLLM args configured")
        return

    logging.info(f"Applying vLLM args: {vllm_args}")

    # Ensure template.containers section exists
    if 'spec' not in isvc_data:
        isvc_data['spec'] = {}
    if 'template' not in isvc_data['spec']:
        isvc_data['spec']['template'] = {}
    if 'containers' not in isvc_data['spec']['template']:
        isvc_data['spec']['template']['containers'] = [{'name': 'main'}]

    # Find the main container
    main_container = None
    for container in isvc_data['spec']['template']['containers']:
        if container.get('name') == 'main':
            main_container = container
            break

    if not main_container:
        main_container = {'name': 'main'}
        isvc_data['spec']['template']['containers'].append(main_container)

    # Ensure env section exists
    if 'env' not in main_container:
        main_container['env'] = []

    # Find or create VLLM_ADDITIONAL_ARGS environment variable
    vllm_args_env = None
    for env_var in main_container['env']:
        if env_var.get('name') == 'VLLM_ADDITIONAL_ARGS':
            vllm_args_env = env_var
            break

    if not vllm_args_env:
        vllm_args_env = {'name': 'VLLM_ADDITIONAL_ARGS', 'value': ''}
        main_container['env'].append(vllm_args_env)

    # Build vLLM arguments
    current_args = vllm_args_env.get('value', '').strip()

    if isinstance(vllm_args, list):
        new_args = vllm_args
    else:
        # Handle string format for backward compatibility
        new_args = [vllm_args]

    # Combine existing and new arguments
    if new_args:
        if current_args:
            combined_args = f"{current_args} {' '.join(new_args)}"
        else:
            combined_args = ' '.join(new_args)

        vllm_args_env['value'] = combined_args
        logging.info(f"Set VLLM_ADDITIONAL_ARGS: {combined_args}")






def apply_gpu_resources(main_container, gpu_count):
    """
    Set GPU resource requests and limits based on tensor parallel size

    Args:
        main_container: The main container definition
        gpu_count: Number of GPUs needed (tensor_parallel_size)
    """
    # Ensure resources section exists
    if 'resources' not in main_container:
        main_container['resources'] = {}
    if 'requests' not in main_container['resources']:
        main_container['resources']['requests'] = {}
    if 'limits' not in main_container['resources']:
        main_container['resources']['limits'] = {}

    # Set GPU resources
    main_container['resources']['requests']['nvidia.com/gpu'] = str(gpu_count)
    main_container['resources']['limits']['nvidia.com/gpu'] = str(gpu_count)

    logging.info(f"Set GPU resources: nvidia.com/gpu={gpu_count} (for TP size {gpu_count})")


def apply_extra_properties(isvc_data):
    """
    Apply extra properties from configuration to the ISVC

    Allows injecting arbitrary YAML properties using dotted-key notation.
    Example config:
        tests.llmd.inference_service.extra_properties:
          spec.template.affinity:
            nodeAffinity:
              requiredDuringSchedulingIgnoredDuringExecution:
                nodeSelectorTerms:
                - matchExpressions:
                  - key: kubernetes.io/hostname
                    operator: NotIn
                    values:
                    - gf48e48

    Args:
        isvc_data: The loaded YAML data structure
    """
    extra_properties = config.project.get_config("tests.llmd.inference_service.extra_properties", {})

    if not extra_properties:
        logging.debug("No extra properties configured")
        return

    logging.info(f"Applying {len(extra_properties)} extra properties to ISVC")

    for dotted_key, value in extra_properties.items():
        _set_nested_property(isvc_data, dotted_key, value)
        logging.info(f"Applied extra property: {dotted_key}")


def _set_nested_property(data, dotted_key, value):
    """
    Set a nested property in a dict using dotted notation

    Args:
        data: Dictionary to modify
        dotted_key: Key path like 'spec.template.affinity'
        value: Value to set
    """
    keys = dotted_key.split('.')
    current = data

    # Navigate to the parent of the final key
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    # Set the final value
    final_key = keys[-1]
    current[final_key] = value


def reshape_isvc(flavor, llmisvc_path):
    """
    Reshape the ISVC YAML file based on configuration

    This method applies various modifications to the ISVC in a modular way:
    1. Flavor-specific modifications (routing, replicas, etc.)
    2. Kueue annotations and labels
    3. Model configuration
    4. vLLM arguments
    5. Extra properties (arbitrary YAML injection)

    Args:
        flavor: The flavor string to apply
        llmisvc_path: Path to the original ISVC YAML file

    Returns:
        Path to the modified ISVC YAML file
    """
    logging.info(f"Reshaping ISVC for flavor: {flavor}")

    # Load the YAML file
    with open(llmisvc_path, 'r') as f:
        isvc_data = yaml.safe_load(f)

    # Apply modifications in order
    apply_flavor_modifications(isvc_data, flavor)
    apply_kueue_configuration(isvc_data)
    apply_model_configuration(isvc_data)
    apply_vllm_args_configuration(isvc_data)
    apply_extra_properties(isvc_data)

    # Save the modified file to ARTIFACT_DIR
    output_path = env.ARTIFACT_DIR / llmisvc_path.name
    try:
        with open(output_path, 'w') as f:
            yaml.dump(isvc_data, f, default_flow_style=False)
    except Exception as e:
        raise ValueError(f"Failed to write reshaped ISVC file to {output_path}: {e}")

    logging.info(f"Reshaped ISVC saved to: {output_path}")
    return output_path


def deploy_llm_inference_service(flavor, llmisvc_name, namespace):
    """
    Deploys the LLM inference service
    """

    llmisvc_file = config.project.get_config("tests.llmd.inference_service.yaml_file")

    # Convert relative path to absolute
    llmisvc_path = pathlib.Path(llmisvc_file)
    if not llmisvc_path.is_absolute():
        llmisvc_path = TESTING_THIS_DIR / "llmisvcs" / llmisvc_path

    llmisvc_path = reshape_isvc(flavor, llmisvc_path)

    if config.project.get_config("tests.llmd.inference_service.skip_deployment"):
        logging.info("Skipping the deployment LLM inference service "
                     f"{llmisvc_name} in namespace {namespace}")
    else:
        logging.info(f"Deploying LLM inference service {llmisvc_name} in namespace {namespace}")

        # Deploy the inference service
        run.run_toolbox("llmd", "deploy_llm_inference_service",
                        name=llmisvc_name,
                        namespace=namespace,
                        yaml_file=llmisvc_path)

    return llmisvc_name, namespace, llmisvc_path


def get_llm_inference_url(llmisvc_name, namespace, flavor):
    """
    Gets the URL of the deployed LLM inference service
    """

    logging.info(f"Getting LLM inference service URL for flavor: {flavor}")

    # Parse flavor components
    components = parse_flavor_components(flavor)
    base_flavor = components['base']

    # For intelligent-routing flavors, get the gateway-internal URL from status
    if base_flavor in ["intelligentrouting", "intelligent-routing"]:
        logging.info("Intelligent-routing flavor detected - looking up gateway-internal URL from status")

        # Get the LLMInferenceService status addresses
        addresses_result = run.run(f"oc get llminferenceservice {llmisvc_name} -n {namespace} "
                                  f"-o jsonpath='{{.status.addresses}}'",
                                  capture_stdout=True, check=False)

        if addresses_result.returncode != 0:
            raise RuntimeError(f"Failed to get LLMInferenceService addresses: {addresses_result.stderr}")

        # Parse the addresses JSON to find gateway-internal URL
        import json
        try:
            addresses = json.loads(addresses_result.stdout)
            gateway_internal_url = None

            for address in addresses:
                if address.get('name') == 'gateway-internal':
                    gateway_internal_url = address.get('url')
                    break

            if not gateway_internal_url:
                raise RuntimeError("gateway-internal URL not found in LLMInferenceService status addresses")

            logging.info(f"Intelligent-routing flavor - using gateway-internal URL: {gateway_internal_url}")
            return gateway_internal_url

        except (json.JSONDecodeError, KeyError) as e:
            raise RuntimeError(f"Failed to parse LLMInferenceService addresses: {e}")

    # For simple flavors, we need to append the HTTPS port from the service
    elif base_flavor == "simple":
        logging.info("Simple flavor detected - looking up service port")

        service_name = f"{llmisvc_name}-kserve-workload-svc"

        # Get the HTTPS port from the service
        port_result = run.run(f"oc get svc {service_name} -n {namespace} "
                              """-o jsonpath='{.spec.ports[?(@.name==\"https\")].port}'""",
                             capture_stdout=True, check=False)

        if port_result.returncode != 0 or not port_result.stdout.strip():
            raise RuntimeError("Couldn't extract the SVC port :/")
        https_port = port_result.stdout.strip()
        endpoint_url = f"https://{service_name}.{namespace}.svc.cluster.local:{https_port}"
        logging.info(f"Simple flavor - using port {https_port} from service")

        return endpoint_url

    else:
        # For other flavors, use standard URL without port
        service_name = f"{llmisvc_name}-kserve-workload-svc"
        endpoint_url = f"https://{service_name}.{namespace}.svc.cluster.local"
        logging.info(f"Other flavor - using standard URL without port: {endpoint_url}")

        return endpoint_url


def run_multiturn_benchmark(endpoint_url, llmisvc_name, namespace):
    """
    Runs the multi-turn benchmark
    """

    if not config.project.get_config("tests.llmd.benchmarks.multiturn.enabled"):
        return False

    logging.info("Running multi-turn benchmark")

    benchmark_name = config.project.get_config("tests.llmd.benchmarks.multiturn.name")
    parallel = config.project.get_config("tests.llmd.benchmarks.multiturn.parallel")
    timeout = config.project.get_config("tests.llmd.benchmarks.multiturn.timeout")

    failed = False

    endpoint_url = f"{endpoint_url}/v1"

    try:
        run.run_toolbox("llmd", "run_multiturn_benchmark",
                       endpoint_url=endpoint_url,
                       name=benchmark_name,
                       namespace=namespace,
                       parallel=parallel,
                       timeout=timeout)

        logging.info("Multi-turn benchmark completed successfully")

    except Exception as e:
        logging.error(f"Multi-turn benchmark failed: {e}")
        failed = True

    return failed


def run_guidellm_benchmark(endpoint_url, llmisvc_name, namespace):
    """
    Runs the Guidellm benchmark
    """

    if not config.project.get_config("tests.llmd.benchmarks.guidellm.enabled"):
        return False

    logging.info("Running Guidellm benchmark")

    benchmark_name = config.project.get_config("tests.llmd.benchmarks.guidellm.name")
    rate = config.project.get_config("tests.llmd.benchmarks.guidellm.rate")
    max_seconds = config.project.get_config("tests.llmd.benchmarks.guidellm.max_seconds")
    timeout = config.project.get_config("tests.llmd.benchmarks.guidellm.timeout")
    data = config.project.get_config("tests.llmd.benchmarks.guidellm.data")

    failed = False

    try:
        run.run_toolbox("llmd", "run_guidellm_benchmark",
                       endpoint_url=endpoint_url,
                       name=benchmark_name,
                       namespace=namespace,
                       rate=rate,
                       max_seconds=max_seconds,
                       timeout=timeout,
                       data=data)

        logging.info("Guidellm benchmark completed successfully")

    except Exception as e:
        logging.error(f"Guidellm benchmark failed: {e}")
        failed = True

    return failed


def capture_llm_inference_service_state(llmisvc_name, namespace):
    """
    Captures the state of the LLM inference service
    """

    logging.info("Capturing LLM inference service state")

    try:
        run.run_toolbox("llmd", "capture_isvc_state",
                       llmisvc_name=llmisvc_name,
                       namespace=namespace, mute_stdout=True)

        logging.info("LLM inference service state captured successfully")

    except Exception as e:
        logging.error(f"Failed to capture LLM inference service state: {e}")


def cleanup_llm_inference_resources():
    """
    Clean up all llminferenceservice resources in the namespace before testing.
    Fails the test if cleanup is not successful.
    """

    namespace = config.project.get_config("tests.llmd.namespace")
    logging.info(f"Cleaning up all jobs resources in namespace {namespace}")
    result = run.run(f"oc delete jobs --all -n {namespace}", capture_stdout=True)

    logging.info(f"Cleaning up all llminferenceservice resources in namespace {namespace}")

    # Delete all llminferenceservice resources in the namespace
    logging.info("Deleting all llminferenceservice resources")
    run.run(f"oc delete llminferenceservice --all -n {namespace} --wait=true --timeout=180s")

    # Verify no llminferenceservice resources remain
    logging.info("Verifying no llminferenceservice resources remain")
    for i in range(6):  # Check up to 6 times with 10 second intervals
        result = run.run(f"oc get llminferenceservice -n {namespace} --no-headers",
                       capture_stdout=True)

        if not result.stdout.strip():
            logging.info("No llminferenceservice resources found - cleanup successful")
            break
        else:
            remaining_services = result.stdout.strip().split('\n')
            remaining_count = len([s for s in remaining_services if s.strip()])
            logging.info(f"Still found {remaining_count} llminferenceservice resources, waiting...")

            if i == 5:  # Last iteration
                logging.error(f"Failed to clean up llminferenceservice resources after 60 seconds. {remaining_count} resources still exist:")
                for service in remaining_services:
                    if service.strip():
                        logging.error(f"  - {service}")
                raise RuntimeError(f"Cannot proceed with test - {remaining_count} llminferenceservice resources still exist in namespace {namespace}")

            time.sleep(10)

    logging.info("LLM inference service cleanup completed successfully")


def ensure_gpu_nodes_available():
    """
    Ensures that there are GPU nodes available in the cluster.
    This function assumes prepare_gpu() has already been called.
    """

    logging.info("Verifying GPU nodes are available in the cluster")

    try:
        result = run.run("oc get nodes -l nvidia.com/gpu.present=true --no-headers", capture_stdout=True)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to check GPU nodes: {result.stderr}")

        gpu_nodes = result.stdout.strip().split('\n') if result.stdout.strip() else []
        has_gpu_nodes = gpu_nodes and not (len(gpu_nodes) == 1 and gpu_nodes[0] == '')

        if not has_gpu_nodes:
            raise RuntimeError("No GPU nodes found in the cluster. GPU nodes are required for LLM inference testing. Ensure prepare_gpu() was called.")
        else:
            logging.info(f"Found {len(gpu_nodes)} GPU node(s) in the cluster")
            for node in gpu_nodes:
                node_name = node.split()[0]
                logging.info(f"  - {node_name}")

    except Exception as e:
        logging.error(f"GPU node validation failed: {e}")
        raise


def test_llm_inference_simple(endpoint_url, llmisvc_name, namespace, model_name):
    """
    Runs a simple test against the LLM inference service using oc rsh
    """

    logging.info("Running simple LLM inference test from inside cluster")

    # Construct the internal service URL
    deployment_name = f"{llmisvc_name}-kserve"

    logging.info(f"Testing internal URL: {endpoint_url}")

    # Test with a simple completion request
    test_payload = {
        "model": model_name,
        "prompt": "San Francisco is a",
        "max_tokens": 50,
        "temperature": 0.7
    }

    try:
        # Convert payload to JSON string for inline use
        payload_json = json.dumps(test_payload)

        # Execute curl inside the pod with inline JSON
        result = run.run(f"""
oc rsh -n {namespace} -c main deploy/{deployment_name} \\
  curl -k -sSf "{endpoint_url}/v1/completions" \\
  -H "Content-Type: application/json" \\
  -d '{payload_json}'
""", capture_stdout=True)

        if result.returncode != 0:
            logging.error(f"Request failed: {result.stderr}")
            return False

        response = json.loads(result.stdout)
        if "choices" not in response or not len(response["choices"]):
            logging.error(f"Invalid response format: {result.stdout}")
            return False

        completion = response["choices"][0]["text"]
        logging.info(f"Simple LLM test successful. Completion: {test_payload['prompt']} ... {completion[:100]}")

        return True

    except Exception as e:
        logging.error(f"Simple LLM test failed: {e}")
        return False


def conditional_scale_up():
    """
    Conditionally scales up GPU nodes if scale_up preset is enabled and no GPU nodes exist
    """
    auto_scale = config.project.get_config("prepare.cluster.nodes.auto_scale")
    if not auto_scale:
        return

    logging.info("Auto scale enabled, checking for existing GPU nodes")

    try:
        result = run.run("oc get nodes -l nvidia.com/gpu.present=true --no-headers", capture_stdout=True)
        gpu_nodes = result.stdout.strip().split('\n') if result.stdout.strip() else []
        has_gpu_nodes = gpu_nodes and not (len(gpu_nodes) == 1 and gpu_nodes[0] == '')

        if not has_gpu_nodes:
            logging.info("No GPU nodes found, scaling up cluster")

            prepare_llmd.scale_up()
        else:
            logging.info(f"Found {len(gpu_nodes)} existing GPU node(s), skipping scale up")

    except Exception as e:
        logging.error(f"Failed to check/scale GPU nodes: {e}")
        raise


def conditional_scale_down():
    """
    Conditionally scales down GPU nodes if scale_up preset is enabled
    """
    auto_scale_down = config.project.get_config("prepare.cluster.nodes.auto_scale_down_on_exit")
    if not auto_scale_down:
        return

    node_instance_type = config.project.get_config("prepare.cluster.nodes.instance_type")
    if not node_instance_type:
        logging.warning("Node instance type not configured, skipping scale down")
        return

    logging.info("Auto scale down enabled, scaling down GPU nodes to 0")

    try:
        run.run_toolbox("cluster", "set_scale",
                       instance_type=node_instance_type,
                       scale=0, mute_stdout=True)
        logging.info("GPU nodes scaled down successfully")
    except Exception as e:
        logging.error(f"Failed to scale down GPU nodes: {e}")


def matbench_run_one():
    """
    Runs one test as part of a MatrixBenchmark benchmark
    """

    logging.info("Running MatrixBenchmark test")

    # Deploy and test (test() now handles its own GPU scaling)
    failed = test()

    if not failed:
        logging.info("MatrixBenchmark test completed successfully")
    else:
        logging.error("MatrixBenchmark test failed")

    return failed
