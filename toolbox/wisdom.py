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
                     model_serving_config_template_path, 
                     serving_runtime_template_path, 
                     inference_service_template_path):
        """
        Deploy Ansible Wisdom model (ServingRuntime and InferenceService)
        # TODO: Allow for configuring the runtime and model version at this level

        Args:
          replicas: Model Mesh Deployment replicas
          s3_secret_path: File path to a yaml manifest for the Secret containing
                          credentials for the S3 bucket with the model files
          quay_pull_secret_path: File path to a yaml manifest for the Secret containing
                                 credentials for the quay repository containing the runtime image.
          protos_path: File path to the proto files needed to query the model
          model_serving_config_template_path: File path to the template for the model-serving-config
                                              ConfigMap
          serving_runtime_template_path: File path to the template for the ServingRuntime YAML
          inference_service_template_path: File path to the template for the InferenceService YAML
        """

        return RunAnsibleRole(locals())

    
    @AnsibleRole("wisdom_warmup_model")
    @AnsibleMappedParams
    def warmup_model(self, protos_path):
        """
        Deploy Ansible Wisdom model (ServingRuntime)
        # TODO: Allow for configuring the runtime and model version at this level

        Args:
          protos_path: Path to protos directory to put into a ConfigMap, and mounted in Pod
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
                          protos_path):
        """
        Deploy Ansible Wisdom model (ServingRuntime)

        Args:
          requests: Requests sent for each model input in the dataset (will be set in llm-load-test config.json)
          concurrency: Number of concurrent simulated users sending requests
          replicas: Model Mesh Deployment replicas currently configured (to be attached as metadata to the results)
          dataset_path: File path to the json file containing the inputs to be used in the load test
          s3_secret_path: File path to an aws credentials file allowing llm-load-test to push the results to S3
          protos_path: File path to the proto files needed to query the model
        """

        return RunAnsibleRole(locals())


   