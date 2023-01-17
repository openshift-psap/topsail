from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleConstant, AnsibleSkipConfigGeneration, AnsibleMappedParams


class NFDOperator:
    """
    Commands for deploying, building and testing the NFD operator in various ways
    """

    @AnsibleRole("cluster_deploy_operator")
    @AnsibleSkipConfigGeneration # see cluster.deploy_operator
    @AnsibleConstant("", "catalog", "redhat-operators")
    @AnsibleConstant("", "manifest_name", "nfd")
    @AnsibleConstant("", "namespace", "openshift-nfd")
    @AnsibleConstant("", "deploy_cr", True)
    @AnsibleMappedParams
    def deploy_from_operatorhub(self, channel=''):
        """
        Deploys the GPU Operator from OperatorHub

        Args:
            channel: The operator hub channel to deploy. e.g. 4.7
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("nfd_operator_undeploy_from_operatorhub")
    @AnsibleMappedParams
    @AnsibleSkipConfigGeneration # see cluster.undeploy_operator
    def undeploy_from_operatorhub(self):
        """
        Undeploys an NFD-operator that was deployed from OperatorHub
        """
        return RunAnsibleRole()
