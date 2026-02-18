import sys
import logging

from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams, AnsibleConstant,
    AnsibleSkipConfigGeneration
)

class Llmd:
    """
    Commands and utilities for the LLM-D toolbox
    """

    @AnsibleRole("llmd_deploy_gateway")
    @AnsibleMappedParams
    def deploy_gateway(self, name="openshift-ai-inference", gateway_class="data-science-gateway-class", namespace="openshift-ingress"):
        """
        Deploys a GatewayClass and Gateway object

        Default gateway class is created by the DSCI -> GatewayConfig/default-gateway -> GatewayClass/data-science-gateway-class

        Args:
          name: Name of the gateway to deploy
          gateway_class: Name of the gateway class to deploy
        """

        if name != "openshift-ai-inference":
            logging.error("Currently the gateway name must be 'openshift-ai-inference'")
            raise SystemExit(1)

        return RunAnsibleRole(locals())

    @AnsibleRole("llmd_deploy_llm_inference_service")
    @AnsibleMappedParams
    def deploy_llm_inference_service(self, name, namespace, yaml_file):
        """
        Deploys an LLM InferenceService from a YAML file

        Args:
          name: Name of the inference service to deploy
          namespace: Namespace to deploy the inference service in
          yaml_file: Path to the YAML file containing the LLMInferenceService
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("llmd_run_multiturn_benchmark")
    @AnsibleMappedParams
    def run_multiturn_benchmark(
            self,
            llmisvc_name,
            name="multi-turn-benchmark", namespace="",
            image="quay.io/hayesphilip/multi-turn-benchmark", version="0.0.1",
            timeout=900, parallel=9
    ):
        """
        Runs a multi-turn benchmark job against the LLM inference service

        Args:
          llmisvc_name: Name of the LLMInferenceService to benchmark (in same namespace)
          name: Name of the benchmark job
          namespace: Namespace to run the benchmark job in (empty string auto-detects current namespace)
          image: Container image for the benchmark
          version: Version tag for the benchmark image
          timeout: Timeout in seconds to wait for job completion
          parallel: Number of parallel connections
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("llmd_run_guidellm_benchmark")
    @AnsibleMappedParams
    def run_guidellm_benchmark(
            self,
            llmisvc_name,
            name="guidellm-benchmark", namespace="",
            image="ghcr.io/vllm-project/guidellm", version="v0.5.3",
            timeout=900, profile="sweep", max_seconds=30,
            processor="RedHatAI/Meta-Llama-3.1-8B-Instruct-FP8-dynamic",
            data="prompt_tokens=256,output_tokens=128"
    ):
        """
        Runs a Guidellm benchmark job against the LLM inference service

        Args:
          llmisvc_name: Name of the LLMInferenceService to benchmark (in same namespace)
          name: Name of the benchmark job
          namespace: Namespace to run the benchmark job in (empty string auto-detects current namespace)
          image: Container image for the benchmark
          version: Version tag for the benchmark image
          timeout: Timeout in seconds to wait for job completion
          profile: Guidellm profile to use
          max_seconds: Maximum seconds to run benchmark
          processor: Model processor name
          data: Data configuration
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("llmd_capture_isvc_state")
    @AnsibleMappedParams
    def capture_isvc_state(
            self,
            llmisvc_name,
            namespace=""
    ):
        """
        Captures all relevant objects and state for an LLMInferenceService

        Args:
          llmisvc_name: Name of the LLMInferenceService to capture
          namespace: Namespace of the LLMInferenceService (empty string auto-detects current namespace)
        """

        return RunAnsibleRole(locals())
