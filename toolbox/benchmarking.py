from toolbox._common import RunAnsibleRole, AnsibleRole


class Benchmarking:
    """
    Commands related to benchmarking tasks
    """

    @AnsibleRole("benchmarking_deploy_coco_dataset")
    def download_coco_dataset(self, node_hostname, namespace="default", pvc_name=None, storage_dir=None, s3_cred=None):
        """
        Downloads the COCO dataset into a PVC of the cluster

        Args:
            node_hostname: Hostname of the node where the download pod will be executed.
            namespace: Name of the namespace in which the resources will be created.
            pvc_name: Name of the PVC that will be create to store the dataset files.
            s3_cred: Optional path to credentials to use for accessing the dataset s3 bucket.
        """
        opts = {
            "benchmarking_node_hostname": node_hostname,
            "benchmarking_namespace": namespace,
        }
        if pvc_name is not None:
            opts["benchmarking_coco_dataset_pvc_name"] = pvc_name
            print(
                f"Using '{pvc_name}' as PVC name."
            )

        if storage_dir is not None:
            opts["benchmarking_coco_dataset_storage_dir"] = storage_dir
            print(
                f"Using '{storage_dir}' as storage dir."
            )

        if s3_cred is not None:
            opts["benchmarking_coco_dataset_s3_cred"] = s3_cred
            print(
                f"Using '{s3_cred}' as s3 credentials."
            )

        return RunAnsibleRole(opts)

    @AnsibleRole("benchmarking_run_mlperf_ssd")
    def run_mlperf_ssd(self, node_hostname, namespace="default", pvc_name=None, epochs=None, threshold=None):
        """
        Run NVIDIA MLPerf SSD Detection training benchmark.

        Args:
            node_hostname: Hostname of the node where the ssd benchmark will be executed.
            namespace: Name of the namespace in which the resources will be created.
            pvc_name: Name of the PVC that will be create to store the dataset files.
            epochs: Number of epochs to run the benchmark for.
            threshold: Benchmark threshold target value.
        """

        opts = {
            "benchmarking_node_hostname": node_hostname,
            "benchmarking_namespace": namespace,
        }

        if pvc_name is not None:
            opts["benchmarking_coco_dataset_pvc_name"] = pvc_name
            print(
                f"Using '{pvc_name}' as PVC where the coco dataset is stored."
            )

        if epochs:
            try:
                epochs = str(int(epochs))
                opts["benchmarking_epochs"] = epochs
            except ValueError:
                print("ERROR: epochs must be of type int")
                exit(1)
        if threshold:
            try:
                threshold = str(float(threshold))
                opts["benchmarking_threshold"] = threshold
            except ValueError:
                print("ERROR: threshold must be of type float")
                exit(1)

        return RunAnsibleRole(opts)
