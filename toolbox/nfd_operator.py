from toolbox._common import RunAnsibleRole, AnsibleRole


class NFDOperator:
    """
    Commands for deploying, building and testing the NFD operator in various ways
    """
    @AnsibleRole("nfd_operator_deploy_custom_commit")
    def deploy_from_commit(self, git_repo, git_ref, image_tag=None):
        """
        Deploys the NFD operator from the given git commit

        Args:
            git_rep: The git repository to deploy from, e.g. https://github.com/openshift/cluster-nfd-operator.git
            git_ref: The git ref to deploy from, e.g. master
            image_tag: The NFD operator image tag UID.
        """
        opts = {
            "nfd_operator_git_repo": git_repo,
            "nfd_operator_git_ref": git_ref,
        }

        if image_tag is not None:
            opts["nfd_operator_image_tag"] = image_tag

        return RunAnsibleRole(opts)

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
