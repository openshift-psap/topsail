from toolbox._common import RunAnsibleRole, AnsibleRole


class NFD:
    """
    Commands for NFD related tasks
    """
    @AnsibleRole("nfd_test_wait_gpu")
    def has_gpu_nodes(self):
        """
        Checks if the cluster has GPU nodes
        """
        return RunAnsibleRole()

    @AnsibleRole("nfd_has_labels")
    def has_labels(self):
        """
        Checks if the cluster has NFD labels
        """
        return RunAnsibleRole()

    @AnsibleRole("nfd_test_wait_gpu")
    def wait_gpu_nodes(self):
        """
        Wait until nfd find GPU nodes
        """
        opts = {
            "nfd_wait_gpu_nodes": "yes"
        }
        return RunAnsibleRole(opts)

    @AnsibleRole("nfd_test_wait_labels")
    def wait_labels(self):
        """
        Wait until nfd labels the nodes
        """
        return RunAnsibleRole()
