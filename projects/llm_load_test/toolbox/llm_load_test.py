import sys

from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams, AnsibleConstant,
    AnsibleSkipConfigGeneration
)

class Llm_Load_Test:
    """
    Commands relating to llm-load-test
    """

    @AnsibleRole("llm_load_test_run")
    @AnsibleMappedParams
    def run(self,
            host,
            port,
            duration,
            plugin="tgis_grpc_plugin",
            interface="grpc",
            model_id="not-used",
            src_path="projects/llm_load_test/subprojects/llm-load-test/",
            streaming=True,
            use_tls=False,
            concurrency=16,
            min_input_tokens=0,
            min_output_tokens=0,
            max_input_tokens=1024,
            max_output_tokens=512,
            max_sequence_tokens=1536,
            endpoint="/v1/completions",
            ):
        """
        Load test the wisdom model

        Args:
          host: the host endpoint of the gRPC call
          port: the gRPC port on the specified host
          duration: the duration of the load testing

          plugin: the llm-load-test plugin to use (tgis_grpc_plugin or caikit_client_plugin for now)
          interface: (http or grpc) the interface to use for llm-load-test-plugins that support both
          model_id: The ID of the model to pass along with the GRPC call
          src_path: Path where llm-load-test has been cloned
          streaming: Whether to stream the llm-load-test requests
          use_tls: Whether to set use_tls: True (grpc in Serverless mode)
          concurrency: Number of concurrent simulated users sending requests
          min_input_tokens: min input tokens in llm load test to filter the dataset
          min_output_tokens: min output tokens in llm load test to filter the dataset
          max_input_tokens: max input tokens in llm load test to filter the dataset
          max_sequence_tokens: max sequence tokens in llm load test to filter the dataset
          max_output_tokens: max output tokens in llm load test to filter the dataset
          endpoint: name of the endpoint to query (for openai plugin only)
        """

        return RunAnsibleRole(locals())
