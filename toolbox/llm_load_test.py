import sys

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration


class Llm_load_test:
    """
    Commands relating to llm-load-test
    """

    @AnsibleRole("llm_load_test_run")
    @AnsibleMappedParams
    def run(self,
            host,
            duration,
            protos_path,
            call,
            model_id,
            llm_path="/src/llm-load-test/",
            threads=16,
            rps=2,
            ):
        """
        Load test the wisdom model

        Args:
          host: the host endpoint of the GRPC call
          duration: the duration of the load testing

          concurrency: Number of concurrent simulated users sending requests

          model_id: The ID of the model to pass along with the GRPC call
          protos_path: File path to the proto files needed to query the model
          call: GRPC call to perform

          llm_path: Path where llm-load-test has been cloned

          threads: number of GHZ instances to launch in parallel
          rps: max request per second
        """

        return RunAnsibleRole(locals())
