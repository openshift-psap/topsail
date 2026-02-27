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

def test():
    """
    Runs the main LLM-D test
    """

    if config.project.get_config("tests.llmd.skip"):
        logging.info("LLM-D test skipped")
        return False

    logging.info("Running LLM-D test")

    prepare_for_test()

    # Get test flavors from config
    flavors = config.project.get_config("tests.llmd.flavors")
    if not isinstance(flavors, list):
        flavors = [flavors]

    logging.info(f"Running tests for flavors: {flavors}")

    overall_failed = False
    test_directory = None
    namespace = config.project.get_config("tests.llmd.namespace")

    with env.NextArtifactDir("llm_d_testing"):
        test_directory = env.ARTIFACT_DIR

        for i, flavor in enumerate(flavors):
            logging.info(f"Running test for flavor: {flavor} ({i+1}/{len(flavors)})")

            flavor_failed = False
            prom_start_ts = None

            llmisvc_name = config.project.get_config("tests.llmd.inference_service.name")
            llmisvc_name += f"-{flavor}"

            with env.NextArtifactDir(f"flavor_{flavor}"):
                try:
                    # Clean up any existing LLM inference services and pods before testing
                    cleanup_llm_inference_resources()

                    # Reset Prometheus before testing
                    if config.project.get_config("tests.capture_prom"):
                        logging.info("Resetting Prometheus database before testing")
                        prom_start_ts = prom.reset_prometheus()

                    # Deploy LLM inference service
                    deploy_llm_inference_service(flavor, llmisvc_name, namespace)

                    # Get the service URL
                    endpoint_url = get_llm_inference_url(llmisvc_name, namespace)
                    if config.project.get_config("tests.llmd.inference_service.do_simple_test"):
                        if not test_llm_inference_simple(endpoint_url, llmisvc_name, namespace):
                            raise RuntimeException("Simple inference test failed :/")

                    # Run benchmarks
                    if config.project.get_config("tests.llmd.benchmarks.multiturn.enabled"):
                        flavor_failed |= run_multiturn_benchmark(endpoint_url, llmisvc_name, namespace)

                    if config.project.get_config("tests.llmd.benchmarks.guidellm.enabled"):
                        flavor_failed |= run_guidellm_benchmark(endpoint_url, llmisvc_name, namespace)

                    # Capture state for analysis
                    capture_llm_inference_service_state(llmisvc_name, namespace)

                except Exception as e:
                    logging.exception(f"Test failed for flavor {flavor} :/")
                    flavor_failed = e

                finally:
                    # Always dump Prometheus data after testing (success or failure)
                    logging.info("Dumping Prometheus database after testing")
                    namespace = config.project.get_config("tests.llmd.namespace")
                    if prom_start_ts:
                        prom.dump_prometheus(prom_start_ts, namespace)

                # Generate test metadata files for this flavor
                _generate_test_metadata(flavor_failed, flavor)

                if flavor_failed:
                    overall_failed = True
                    logging.error(f"Test failed for flavor: {flavor}")
                else:
                    logging.info(f"Test completed successfully for flavor: {flavor}")

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
    logging.info("Starting parallel GPU readiness check and image preloading")

    with run.Parallel("prepare_gpu_node") as parallel:
        parallel.delayed(prepare_llmd.wait_for_gpu_readiness)
        parallel.delayed(prepare_llmd.preload_llm_model_image)


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


def reshape_isvc(flavor, llmisvc_path):
    """
    Reshape the ISVC YAML file based on the flavor configuration
    """

    logging.info(f"Reshaping ISVC for flavor: {flavor}")

    # Load the YAML file
    with open(llmisvc_path, 'r') as f:
        isvc_data = yaml.safe_load(f)

    # Apply flavor-specific modifications
    if "simple" in flavor:
        logging.info("Applying 'simple' flavor modifications")

        # Remove spec.router if it exists
        del isvc_data['spec']['router']
        logging.info("Removed spec.router for 'simple' flavor")

    elif "intelligent-routing" in flavor or "default" in flavor:
        logging.info("Applying 'intelligent-routing' flavor - keeping ISVC untouched")
        # No modifications - keep original ISVC configuration
    else:
        # Unknown flavor
        raise ValueError(f"Unknown flavor '{flavor}'. Supported flavors: simple, intelligent-routing")

    if "x2" in flavor:
        isvc_data['spec']['replicas'] = 2
        logging.info("Setting spec.replicas = 2")

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

    logging.info(f"Deploying LLM inference service {llmisvc_name} in namespace {namespace}")

    # Deploy the inference service
    run.run_toolbox("llmd", "deploy_llm_inference_service",
                   name=llmisvc_name,
                   namespace=namespace,
                   yaml_file=llmisvc_path)

    return llmisvc_name, namespace


def get_llm_inference_url(llmisvc_name, namespace):
    """
    Gets the URL of the deployed LLM inference service
    """

    logging.info("Getting LLM inference service URL")

    # Try getting the service URL from .status.url first
    url_result = run.run(f"oc get llminferenceservice {llmisvc_name} -n {namespace} "
                        f"-ojsonpath='{{.status.url}}'", capture_stdout=True)

    endpoint_url = url_result.stdout.strip() if url_result.returncode == 0 else ""

    if endpoint_url:
        logging.info(f"LLM inference service URL: {endpoint_url}")
        return endpoint_url

    # If that didn't work or is empty, try .status.addresses[0].url
    logging.info("Trying alternate URL location at .status.addresses[0].url")
    url_result = run.run(f"oc get llminferenceservice {llmisvc_name} -n {namespace} "
                         f"-ojsonpath='{{.status.addresses[0].url}}'", capture_stdout=True)

    if url_result.returncode != 0:
        logging.error("Failed to get LLM inference service URL from both locations")
        raise RuntimeError(f"Failed to get LLM inference service URL: {url_result.stderr}")

    endpoint_url = url_result.stdout.strip()

    if not endpoint_url:
        logging.error("LLM inference service URL is empty at both locations")
        raise RuntimeError("LLM inference service URL is empty")

    # Get the service port
    port_result = run.run(f"oc get svc -l app.kubernetes.io/name={llmisvc_name} "
                          f"-n {namespace} -o jsonpath='{{.items[0].spec.ports[0].port}}'", capture_stdout=True)

    if port_result.stdout.strip():
        port = port_result.stdout.strip()

        endpoint_url = f"{endpoint_url}:{port}"
        logging.info(f"Added port {port} to URL: {endpoint_url}")

    logging.info(f"LLM inference service URL: {endpoint_url}")
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
    profile = config.project.get_config("tests.llmd.benchmarks.guidellm.profile")
    max_seconds = config.project.get_config("tests.llmd.benchmarks.guidellm.max_seconds")
    timeout = config.project.get_config("tests.llmd.benchmarks.guidellm.timeout")
    processor = config.project.get_config("tests.llmd.benchmarks.guidellm.processor")
    data = config.project.get_config("tests.llmd.benchmarks.guidellm.data")

    failed = False

    try:
        run.run_toolbox("llmd", "run_guidellm_benchmark",
                       endpoint_url=endpoint_url,
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


def test_llm_inference_simple(endpoint_url, llmisvc_name, namespace):
    """
    Runs a simple test against the LLM inference service using oc rsh
    """

    logging.info("Running simple LLM inference test from inside cluster")

    # Construct the internal service URL
    deployment_name = f"{llmisvc_name}-kserve"

    logging.info(f"Testing internal URL: {endpoint_url}")

    # Test with a simple completion request
    test_payload = {
        "model": "llama-3-1-8b-instruct-fp8",
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
        logging.info(f"Simple LLM test successful. Completion: {completion[:100]}...")

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
