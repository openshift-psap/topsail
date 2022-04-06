from toolbox._common import RunAnsibleRole


class NFD:
    """
    Commands for NFD related tasks
    """
    @staticmethod
    def has_gpu_nodes():
        """
        Checks if the cluster has GPU nodes
        """
        return RunAnsibleRole("nfd_test_wait_gpu")

    @staticmethod
    def has_labels():
        """
        Checks if the cluster has NFD labels
        """
        return RunAnsibleRole("nfd_has_labels")

    @staticmethod
    def wait_gpu_nodes():
        """
        Wait until nfd find GPU nodes
        """
        opts = {
            "nfd_wait_gpu_nodes": "yes"
        }
        return RunAnsibleRole("nfd_test_wait_gpu", opts)

    @staticmethod
    def wait_labels():
        """
        Wait until nfd labels the nodes
        """
        return RunAnsibleRole("nfd_test_wait_labels")
