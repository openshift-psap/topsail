import sys

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration


class Wisdom:
    """
    Commands relating to Wisdom
    """

    @AnsibleRole("wisdom_deploy_model")
    @AnsibleMappedParams
    def deploy_model(self, 
                     replicas, 
                     s3_secret_path, 
                     quay_pull_secret_path, 
                     protos_path, 
                     tester_imagestream_name,
                     tester_image_tag,
                     serving_runtime_name="wisdom-runtime",
                     namespace="wisdom"
                     ):
        """
        Deploy Ansible Wisdom model (ServingRuntime and InferenceService)

        Args:
          replicas: Model Mesh Deployment replicas
          s3_secret_path: File path to a yaml manifest for the Secret containing
                          credentials for the S3 bucket with the model files
          quay_pull_secret_path: File path to a yaml manifest for the Secret containing
                                 credentials for the quay repository containing the runtime image.
          protos_path: File path to the proto files needed to query the model
          tester_imagestream_name: Name for the imagestream for the model validator Pod container image
          tester_image_tag: Name for the tag for the model validator Pod container imagestream
          serving_runtime_name: Name for the wisdom serving runtime.
          namespace: Namespace to deploy the model 
        """

        return RunAnsibleRole(locals())

    
    @AnsibleRole("wisdom_warmup_model")
    @AnsibleMappedParams
    def warmup_model(self,
                     protos_path,
                     tester_imagestream_name,
                     tester_image_tag,
                     concurrency="16",
                     total_requests="4096",
                     namespace="wisdom"):
        """
        Deploy Ansible Wisdom model (ServingRuntime)

        Args:
          protos_path: Path to protos directory to put into a ConfigMap, and mounted in Pod
          tester_imagestream_name: Name for the imagestream for the model validator Pod container image
          tester_image_tag: Name for the tag for the model validator Pod container imagestream
          concurrency: Concurrency value for the wisdom-warmup Pod
          total_requests: Total_requests value for the wisdom-warmup Pod
          warmup_concurrency: Simulated concurrent users for the warmup
          warmup_total_requests: Total maximum requests to send for the warmup phase.
          namespace: Namespace to deploy the model 
        """

        return RunAnsibleRole(locals())
    
    @AnsibleRole("wisdom_llm_load_test")
    @AnsibleMappedParams
    def run_llm_load_test(self, 
                          requests, 
                          concurrency, 
                          replicas, 
                          dataset_path, 
                          s3_secret_path, 
                          protos_path,
                          tester_imagestream_name,
                          tester_image_tag,
                          namespace="wisdom"):
        """
        Load test the wisdom model

        Args:
          requests: Requests sent for each model input in the dataset (will be set in llm-load-test config.json)
          concurrency: Number of concurrent simulated users sending requests
          replicas: Model Mesh Deployment replicas currently configured (to be attached as metadata to the results)
          dataset_path: File path to the json file containing the inputs to be used in the load test
          s3_secret_path: File path to an aws credentials file allowing llm-load-test to push the results to S3
          protos_path: File path to the proto files needed to query the model
          tester_imagestream_name: Name for the imagestream for the model validator Pod container image
          tester_image_tag: Name for the tag for the model validator Pod container imagestream
          namespace: Namespace to deploy the model 
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("wisdom_llm_load_test_multiplexed")
    @AnsibleMappedParams
    def run_llm_load_test_multiplexed(self, 
                          requests, 
                          concurrency, 
                          replicas, 
                          max_duration,
                          dataset_path, 
                          s3_secret_path, 
                          protos_path,
                          tester_imagestream_name,
                          tester_image_tag,
                          namespace="wisdom"):
        """
        Load test the wisdom model with multiplexed requests.

        Args:
          requests: Requests sent for each model input in the dataset (will be set in llm-load-test config.json)
          concurrency: Number of concurrent simulated users sending requests
          replicas: Model Mesh Deployment replicas currently configured (to be attached as metadata to the results)
          max_duration: Max duration value for the launcher
          dataset_path: File path to the json file containing the inputs to be used in the load test
          s3_secret_path: File path to an aws credentials file allowing llm-load-test to push the results to S3
          protos_path: File path to the proto files needed to query the model
          tester_imagestream_name: Name for the imagestream for the model validator Pod container image
          tester_image_tag: Name for the tag for the model validator Pod container imagestream
          namespace: Namespace to deploy the model 
        """

        return RunAnsibleRole(locals())

