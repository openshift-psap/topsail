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
            duration,
            model_id="not-used",
            llm_path="/src/llm-load-test/",
            concurrency=16,
            ):
        """
        Load test the wisdom model

        Args:
          host: the host endpoint of the GRPC call
          duration: the duration of the load testing

          model_id: The ID of the model to pass along with the GRPC call
          protos_path: File path to the proto files needed to query the model
          llm_path: Path where llm-load-test has been cloned
          
          concurrency: Number of concurrent simulated users sending requests
        """

        return RunAnsibleRole(locals())
