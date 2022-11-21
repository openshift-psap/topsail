from toolbox._common import RunAnsibleRole, AnsibleRole


class NFDOperator:
    """
    Commands for deploying, building and testing the NFD operator in various ways
    """

    @AnsibleRole("cluster_deploy_operator")
    def deploy_from_operatorhub(self, channel=None):
        """
        Deploys the GPU Operator from OperatorHub

        Args:
            The operator hub channel to deploy. e.g. 4.7
        """
        opts = {
            "cluster_deploy_operator_catalog": "redhat-operators",
            "cluster_deploy_operator_manifest_name": "nfd",
            "cluster_deploy_operator_namespace": "openshift-nfd",
            "cluster_deploy_operator_deploy_cr": True,
        }

        if channel is not None:
            opts["cluster_deploy_operator_channel"] = channel

        return RunAnsibleRole(opts)

    @AnsibleRole("nfd_operator_undeploy_from_operatorhub")
    def undeploy_from_operatorhub(self):
        """
        Undeploys an NFD-operator that was deployed from OperatorHub
        """
        return RunAnsibleRole()
