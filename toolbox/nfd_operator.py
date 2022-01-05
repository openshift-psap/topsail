from toolbox._common import PlaybookRun


class NFDOperator:
    """
    Commands for deploying, building and testing the NFD operator in various ways
    """
    @staticmethod
    def deploy_from_commit(git_repo, git_ref, image_tag=None):
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

        return PlaybookRun("nfd_operator_deploy_custom_commit", opts)

    @staticmethod
    def deploy_from_operatorhub(channel=None):
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

        return PlaybookRun("cluster_deploy_operator", opts)

    @staticmethod
    def undeploy_from_operatorhub():
        """
        Undeploys an NFD-operator that was deployed from OperatorHub
        """
        return PlaybookRun("nfd_operator_undeploy")
