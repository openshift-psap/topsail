from toolbox._common import RunAnsibleRole, AnsibleRole


class NFD:
    """
    Commands for NFD related tasks
    """
    @staticmethod
    @AnsibleRole("nfd_test_wait_gpu")
    def has_gpu_nodes():
        """
        Checks if the cluster has GPU nodes
        """
        return RunAnsibleRole()

    @staticmethod
    @AnsibleRole("nfd_has_labels")
    def has_labels():
        """
        Checks if the cluster has NFD labels
        """
        return RunAnsibleRole()

    @staticmethod
    @AnsibleRole("nfd_test_wait_gpu")
    def wait_gpu_nodes():
        """
        Wait until nfd find GPU nodes
        """
        opts = {
            "nfd_wait_gpu_nodes": "yes"
        }
        return RunAnsibleRole(opts)

    @staticmethod
    @AnsibleRole("nfd_test_wait_labels")
    def wait_labels():
        """
        Wait until nfd labels the nodes
        """
        return RunAnsibleRole()
