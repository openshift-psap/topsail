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

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent

def test():
    """
    Runs the main LLM-D test
    """

    if config.project.get_config("tests.llmd.skip"):
        logging.info("LLM-D test skipped")
        return False

    logging.info("Running LLM-D test")

    # Handle conditional GPU scaling before test
    conditional_scale_up()

    # Ensure GPU nodes are available before running test
    ensure_gpu_nodes_available()

    # Preload LLM model image on GPU nodes
    preload_llm_model_image()

    failed = False

    with env.NextArtifactDir("llm_d_testing"):
        try:
            # Reset Prometheus before testing
            logging.info("Resetting Prometheus database before testing")
            prom_start_ts = prom.reset_prometheus()

            # Deploy LLM inference service
            deploy_llm_inference_service()

            # Run benchmarks
            if config.project.get_config("tests.llmd.benchmarks.multiturn.enabled"):
                failed |= run_multiturn_benchmark()

            if config.project.get_config("tests.llmd.benchmarks.guidellm.enabled"):
                failed |= run_guidellm_benchmark()

            # Capture state for analysis
            capture_llm_inference_service_state()

        except Exception as e:
            logging.exception(f"Test failed :/")
            failed = True

        finally:
            # Always dump Prometheus data after testing (success or failure)
            logging.info("Dumping Prometheus database after testing")
            namespace = config.project.get_config("tests.llmd.namespace")
            prom.dump_prometheus(prom_start_ts, namespace)

        # Generate test metadata files
        _generate_test_metadata(failed)

    # Handle conditional GPU scaling after test completion
    conditional_scale_down()

    return failed


def _generate_test_metadata(failed):
    """
    Generate metadata files for the test execution
    """
    logging.info("Generating test metadata files")

    # Write exit code file
    exit_code = "1" if failed else "0"
    exit_code_path = env.ARTIFACT_DIR / "exit_code"
    with open(exit_code_path, 'w') as f:
        f.write(exit_code)

    logging.info(f"Written exit code: {exit_code} to {exit_code_path}")

    # Write settings file
    settings_path = env.ARTIFACT_DIR / "settings.yaml"
    with open(settings_path, 'w') as f:
        f.write("llm-d: true\n")

    logging.info(f"Written settings to {settings_path}")


def deploy_llm_inference_service():
    """
    Deploys the LLM inference service
    """

    namespace = config.project.get_config("tests.llmd.namespace")
    llmisvc_name = config.project.get_config("tests.llmd.inference_service.name")
    llmisvc_file = config.project.get_config("tests.llmd.inference_service.yaml_file")

    # Convert relative path to absolute
    if not os.path.isabs(llmisvc_file):
        llmisvc_file = str(TESTING_THIS_DIR / "llmisvcs" / llmisvc_file)

    logging.info(f"Deploying LLM inference service {llmisvc_name} in namespace {namespace}")

    # Deploy the inference service
    run.run_toolbox("llmd", "deploy_llm_inference_service",
                   name=llmisvc_name,
                   namespace=namespace,
                   yaml_file=llmisvc_file)

    # Wait for the service to be ready
    timeout = config.project.get_config("tests.llmd.inference_service.timeout")
    logging.info(f"Waiting up to {timeout}s for LLM inference service to be ready")

    run.run(f"oc wait --for=condition=Ready llminferenceservice/{llmisvc_name} "
           f"-n {namespace} --timeout={timeout}s")

    # Get and log the service URL
    url_result = run.run(f"oc get llminferenceservice {llmisvc_name} -n {namespace} "
                        f"-o jsonpath='{{.status.url}}'", capture_stdout=True)

    if url_result.returncode == 0:
        logging.info(f"LLM inference service URL: {url_result.stdout.strip()}")

    return llmisvc_name, namespace


def run_multiturn_benchmark():
    """
    Runs the multi-turn benchmark
    """

    if not config.project.get_config("tests.llmd.benchmarks.multiturn.enabled"):
        return False

    logging.info("Running multi-turn benchmark")

    llmisvc_name = config.project.get_config("tests.llmd.inference_service.name")
    namespace = config.project.get_config("tests.llmd.namespace")

    benchmark_name = config.project.get_config("tests.llmd.benchmarks.multiturn.name")
    parallel = config.project.get_config("tests.llmd.benchmarks.multiturn.parallel")
    timeout = config.project.get_config("tests.llmd.benchmarks.multiturn.timeout")

    failed = False

    try:
        run.run_toolbox("llmd", "run_multiturn_benchmark",
                       llmisvc_name=llmisvc_name,
                       name=benchmark_name,
                       namespace=namespace,
                       parallel=parallel,
                       timeout=timeout)

        logging.info("Multi-turn benchmark completed successfully")

    except Exception as e:
        logging.error(f"Multi-turn benchmark failed: {e}")
        failed = True

    return failed


def run_guidellm_benchmark():
    """
    Runs the Guidellm benchmark
    """

    if not config.project.get_config("tests.llmd.benchmarks.guidellm.enabled"):
        return False

    logging.info("Running Guidellm benchmark")

    llmisvc_name = config.project.get_config("tests.llmd.inference_service.name")
    namespace = config.project.get_config("tests.llmd.namespace")

    benchmark_name = config.project.get_config("tests.llmd.benchmarks.guidellm.name")
    profile = config.project.get_config("tests.llmd.benchmarks.guidellm.profile")
    max_seconds = config.project.get_config("tests.llmd.benchmarks.guidellm.max_seconds")
    timeout = config.project.get_config("tests.llmd.benchmarks.guidellm.timeout")
    processor = config.project.get_config("tests.llmd.benchmarks.guidellm.processor")
    data = config.project.get_config("tests.llmd.benchmarks.guidellm.data")

    failed = False

    try:
        run.run_toolbox("llmd", "run_guidellm_benchmark",
                       llmisvc_name=llmisvc_name,
                       name=benchmark_name,
                       namespace=namespace,
                       profile=profile,
                       max_seconds=max_seconds,
                       timeout=timeout,
                       processor=processor,
                       data=data)

        logging.info("Guidellm benchmark completed successfully")

    except Exception as e:
        logging.error(f"Guidellm benchmark failed: {e}")
        failed = True

    return failed


def capture_llm_inference_service_state():
    """
    Captures the state of the LLM inference service
    """

    logging.info("Capturing LLM inference service state")

    llmisvc_name = config.project.get_config("tests.llmd.inference_service.name")
    namespace = config.project.get_config("tests.llmd.namespace")

    try:
        run.run_toolbox("llmd", "capture_isvc_state",
                       llmisvc_name=llmisvc_name,
                       namespace=namespace, mute=True)

        logging.info("LLM inference service state captured successfully")

    except Exception as e:
        logging.error(f"Failed to capture LLM inference service state: {e}")


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


def preload_llm_model_image():
    """
    Preloads the LLM model image on GPU nodes to reduce startup time
    """

    logging.info("Preloading LLM model image on GPU nodes")

    try:
        # Get the model image URI from the YAML file
        yaml_file = config.project.get_config("tests.llmd.inference_service.yaml_file")
        namespace = config.project.get_config("tests.llmd.namespace")

        # Extract the model URI using yq
        image_result = run.run(f"cat {yaml_file} | yq .spec.model.uri", capture_stdout=True)

        if image_result.returncode != 0:
            raise RuntimeError(f"Failed to extract model URI from {yaml_file}: {image_result.stderr}")

        model_image = image_result.stdout.strip().strip('"')
        logging.info(f"Preloading model image: {model_image}")

        # Get additional images from RHODS operator CSV
        csv_result = run.run("oc get csv rhods-operator.3.3.0 -ojson | jq '.spec.relatedImages | .[]'", capture_stdout=True)

        if csv_result.returncode != 0:
            logging.warning(f"Failed to get RHODS operator related images: {csv_result.stderr}")
            additional_images = []
        else:
            # Parse the JSON output to get specific images
            import json
            related_images = []
            for line in csv_result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        img_data = json.loads(line)
                        related_images.append(img_data)
                    except json.JSONDecodeError:
                        continue

            # Extract the specific images we need
            target_image_names = [
                "rhaiis_vllm_cuda_image",
                "odh_llm_d_inference_scheduler_image",
                "odh_llm_d_routing_sidecar_image"
            ]

            additional_images = []
            for img in related_images:
                if img.get("name") in target_image_names:
                    additional_images.append(img.get("image"))
                    logging.info(f"Found additional image to preload: {img.get('name')} = {img.get('image')}")

        # Preload all images on GPU nodes
        all_images = [model_image] + additional_images

        for image in all_images:
            if image:
                logging.info(f"Preloading image: {image}")
                run.run_toolbox("cluster", "preload_image",
                               namespace=namespace,
                               node_selector_key="nvidia.com/gpu.present",
                               node_selector_value="true",
                               image=image)

        logging.info("LLM model and related images preloading completed successfully")

    except Exception as e:
        logging.error(f"Failed to preload LLM model image: {e}")
        raise


def test_llm_inference_simple():
    """
    Runs a simple test against the LLM inference service
    """

    namespace = config.project.get_config("tests.llmd.namespace")
    llmisvc_name = config.project.get_config("tests.llmd.inference_service.name")

    logging.info("Running simple LLM inference test")

    # Get the service URL
    url_result = run.run(f"oc get llminferenceservice {llmisvc_name} -n {namespace} "
                        f"-o jsonpath='{{.status.url}}'", capture_stdout=True)

    if url_result.returncode != 0:
        logging.error("Failed to get LLM inference service URL")
        return True

    url = url_result.stdout.strip()
    if not url:
        logging.error("LLM inference service URL is empty")
        return True

    # Test with a simple completion request
    test_payload = {
        "model": "llama-3-1-8b-instruct-fp8",
        "prompt": "San Francisco is a",
        "max_tokens": 50,
        "temperature": 0.7
    }

    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_payload, f)
            payload_file = f.name

        # Make the request
        result = run.run(f"""
curl -s "{url}/v1/completions" \\
  -H "Content-Type: application/json" \\
  -d @{payload_file}
""", capture_stdout=True)

        os.unlink(payload_file)

        if result.returncode == 0:
            response = json.loads(result.stdout)
            if "choices" in response and len(response["choices"]) > 0:
                completion = response["choices"][0].get("text", "")
                logging.info(f"Simple LLM test successful. Completion: {completion[:100]}...")
                return False
            else:
                logging.error(f"Invalid response format: {result.stdout}")
                return True
        else:
            logging.error(f"Request failed: {result.stderr}")
            return True

    except Exception as e:
        logging.error(f"Simple LLM test failed: {e}")
        return True


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

            node_instance_type = config.project.get_config("prepare.cluster.nodes.instance_type")
            node_count = config.project.get_config("prepare.cluster.nodes.count")

            if node_instance_type and node_count:
                logging.info(f"Scaling cluster to {node_count} {node_instance_type} instances")
                run.run_toolbox("cluster", "set_scale",
                               instance_type=node_instance_type,
                               scale=node_count)

                # Wait for GPU nodes to be ready
                logging.info("Waiting for GPU nodes to be ready...")
                run.run_toolbox("nfd", "wait_gpu_nodes")
                run.run_toolbox("gpu-operator", "wait_stack_deployed")
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
                       scale=0)
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
