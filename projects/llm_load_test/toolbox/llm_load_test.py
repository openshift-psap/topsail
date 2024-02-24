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
            llm_path="/src/llm-load-test/",
            concurrency=16,
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
          llm_path: Path where llm-load-test has been cloned
          concurrency: Number of concurrent simulated users sending requests
        """

        return RunAnsibleRole(locals())
