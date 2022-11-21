from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams


class Benchmarking:
    """
    Commands related to benchmarking tasks
    """

    @AnsibleRole("benchmarking_deploy_coco_dataset")
    @AnsibleMappedParams
    def download_coco_dataset(self, node_hostname, namespace="default",
                              pvc_name="", storage_dir="/storage", s3_cred=""):
        """
        Downloads the COCO dataset into a PVC of the cluster

        Args:
            node_hostname: Hostname of the node where the download pod will be executed.
            namespace: Name of the namespace in which the resources will be created.
            pvc_name: Name of the PVC that will be create to store the dataset files.
            s3_cred: Path to credentials to use for accessing the dataset s3 bucket.
            storage_dir: Pod directory where the dataset will be downloaded
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("benchmarking_run_mlperf_ssd")
    @AnsibleMappedParams
    def run_mlperf_ssd(self, node_hostname, namespace="default", pvc_name="",
                       epochs: int = "", threshold: float = ""):
        """
        Run NVIDIA MLPerf SSD Detection training benchmark.

        Args:
            node_hostname: Hostname of the node where the ssd benchmark will be executed.
            namespace: Name of the namespace in which the resources will be created.
            pvc_name: Name of the PVC that will be create to store the dataset files.
            epochs: Number of epochs to run the benchmark for.
            threshold: Benchmark threshold target value.
        """

        if pvc_name is not None:
            print(
                f"Using '{pvc_name}' as PVC where the coco dataset is stored."
            )

        if epochs:
            try:
                epochs = int(epochs)
            except ValueError:
                print("ERROR: epochs must be of type int")
                exit(1)

        if threshold:
            try:
                threshold = float(threshold)
            except ValueError:
                print("ERROR: threshold must be of type float")
                exit(1)

        return RunAnsibleRole(locals())
