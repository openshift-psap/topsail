import sys

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration


class Load_Aware:
    """
    Commands relating to Trimaran and LoadAware testing
    """

    @AnsibleRole("load_aware_deploy_trimaran")
    @AnsibleMappedParams
    def deploy_trimaran(self, log_level=1,
                        plugin="TargetLoadPacking",
                        default_requests_cpu="2000m",
                        default_target_requests_multiplier="2",
                        target_utilization=70,
                        safe_variance_margin=1,
                        safe_variance_sensitivity=2,
                        smoothing_window_size=5,
                        risk_limit_weights_cpu=0.5,
                        risk_limit_weights_memory=0.5
                        ):
        """
        Role to deploy the Trimaran load aware scheduler

        Args:
            log_level: log verbosity to set the scheduler to run with,
            plugin: TargetLoadPacking or LoadVariationRiskBalancing
            default_requests_cpu: TargetLoadPacking setting
            default_target_requests_multiplier: TargetLoadPacking setting
            target_utilization: TargetLoadPacking setting,
            safe_variance_margin: LoadVariationRiskBalancing setting
            safe_variance_sensitivity: LoadVariationRiskBalancing setting
            smoothing_window_size: The window size
            risk_limit_weights_cpu: CPU Limit
            risk_limit_weights_memory: Memory limit
        """

        if plugin not in ("TargetLoadPacking", "LoadVariationRiskBalancing", "LowRiskOverCommitment"):
            print(f"Can't deploy Trimaran with unknown plugin: {plugin}")
            sys.exit(1)


        print(f"Deploying Trimaran with plugin {plugin}")

        if plugin == "TargetLoadPacking":
            print(f"default_requests_cpu: {default_requests_cpu}")
            print(f"default_target_requests_multiplier: {default_target_requests_multiplier}")
            print(f"target_utilization: {target_utilization}")
        elif plugin == "LoadVariationRiskBalancing":
            print(f"safe_variance_margin: {safe_variance_margin}")
            print(f"safe_variance_sensitivity: {safe_variance_sensitivity}")
        else:
            print(f"smoothing_window_size: {smoothing_window_size}")
            print(f"risk_limit_weights_cpu: {risk_limit_weights_cpu}")
            print(f"risk_limit_weights_memory: {risk_limit_weights_memory}")

        print(f"Deploying Trimaran with log level {log_level}")

        return RunAnsibleRole(locals())

    @AnsibleRole("load_aware_undeploy_trimaran")
    @AnsibleMappedParams
    def undeploy_trimaran(self):
        """
        Role to undeploy the Trimaran load aware scheduler
        
        Args:
            None
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("load_aware_scale_test")
    @AnsibleMappedParams
    def scale_test(self, distribution="poisson", duration=60.0, instances=10, namespace="load-aware", scheduler="default", sleep_duration=180):
        """
        Role to run a scale test with a given scheduler

        Args:
            distribution: what distribution to generate the load according to (poisson, normal, bimodal, gamma, or uniform)
            duration: how long the test should last (seconds)
            instances: how many of the workload to launch, at the moment, this is the number of test pods
            namespace: which namespace to run the scale test in (must already exist)
            scheduler: name of the scheduler to use (default, trimaran)
            sleep_duration: how long the sleep pod should sleep
        """

        if distribution not in ("poisson", "normal", "bimodal", "gamma", "uniform"):
            print(f"Can't run scale test using unknown distribution: {distribution}")
            sys.exit(1)

        if scheduler not in ("default", "trimaran"):
            print(f"Can't run scale test with unknown scheduler: {scheduler}")
            sys.exit(1)

        return RunAnsibleRole(locals())
