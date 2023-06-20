import sys

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration


class LoadAware:
    """
    Commands relating to Trimaran and LoadAware testing
    """

    @AnsibleRole("load_aware_deploy_trimaran")
    @AnsibleMappedParams
    def deploy_trimaran(self, log_level=1,
                        plugin="TargetLoadPacking", default_requests_cpu="2000m",
                        default_target_requests_multiplier="2", target_utilization=70,
                        safe_variance_margin=1, safe_variance_sensitivity=2
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
        """

        if plugin not in ("TargetLoadPacking", "LoadVariationRiskBalancing"):
            print(f"Can't deploy Trimaran with unknown plugin: {plugin}")
            sys.exit(1)


        print(f"Deploying Trimaran with plugin {plugin}")

        if plugin == "TargetLoadPacking":
            print(f"default_requests_cpu: {default_requests_cpu}")
            print(f"default_target_requests_multiplier: {default_target_requests_multiplier}")
            print(f"target_utilization: {target_utilization}")
        else:
            print(f"safe_variance_margin: {safe_variance_margin}")
            print(f"safe_variance_sensitivity: {safe_variance_sensitivity}")

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
