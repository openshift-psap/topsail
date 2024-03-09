import sys

from topsail._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration


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
            concurrency=16,
            max_input_tokens=1024,
            max_output_tokens=512,
            max_sequence_tokens=1536,
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
          concurrency: Number of concurrent simulated users sending requests
          max_input_tokens: max input tokens in llm load test to filter the dataset
          max_sequence_tokens: max sequence tokens in llm load test to filter the dataset
          max_output_tokens: max output tokens in llm load test to filter the dataset
        """

        return RunAnsibleRole(locals())
