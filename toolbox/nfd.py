from toolbox._common import PlaybookRun


class NFD:
    """
    Commands for NFD related tasks
    """
    @staticmethod
    def has_gpu_nodes():
        """
        Checks if the cluster has GPU nodes
        """
        return PlaybookRun("nfd_test_wait_gpu")

    @staticmethod
    def has_labels():
        """
        Checks if the cluster has NFD labels
        """
        return PlaybookRun("nfd_has_labels")

    @staticmethod
    def wait_gpu_nodes():
        """
        Wait until nfd find GPU nodes
        """
        opts = {
            "nfd_wait_gpu_nodes": "yes"
        }
        return PlaybookRun("nfd_test_wait_gpu", opts)

    @staticmethod
    def wait_labels():
        """
        Wait until nfd labels the nodes
        """
        return PlaybookRun("nfd_test_wait_labels")
