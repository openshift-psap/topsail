from toolbox._common import PlaybookRun


class Benchmarking:
    """
    Commands related to benchmarking tasks
    """

    @staticmethod
    def download_coco_dataset(node_hostname, namespace="default", pvc_name=None, mirror_base_url=None, client_cert=None):
        """
        Downloads the COCO dataset into a PVC of the cluster

        Args:
            node_hostname: Hostname of the node where the download pod will be executed.
            namespace: Name of the namespace in which the resources will be created.
            pvc_name: Name of the PVC that will be create to store the dataset files.
            mirror_base_url: Optional base URL where to fetch the dataset
            client_cert: Optional tath to the client cert to use for accessing the base URL.
        """
        opts = {
            "benchmarking_node_hostname": node_hostname,
            "benchmarking_namespace": namespace,
        }
        if pvc_name is not None:
            opts["benchmarking_coco_dataset_pvc_name"] = pvc_name,
            print(
                f"Using '{pvc_name}' as PVC name."
            )

        if mirror_base_url is not None:
            opts["benchmarking_coco_dataset_mirror_base_url"] = mirror_base_url
            print(
                f"Using '{mirror_base_url}' as mirror base URL."
            )

        if client_cert is not None:
            opts["benchmarking_coco_dataset_client_cert"] = client_cert
            print(
                f"Using '{client_cert}' as client certificate."
            )

        return PlaybookRun("benchmarking_deploy_coco_dataset", opts)

    @staticmethod
    def run_nvidiadl_ssd(node_hostname, namespace="default", pvc_name=None):
        """
        Run NVIDIA Deep Learning SSD Detection training benchmark.

        Args:
            node_hostname: Hostname of the node where the ssd benchmark will be executed.
            namespace: Name of the namespace in which the resources will be created.
            pvc_name: Name of the PVC that will be create to store the dataset files.
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
        return PlaybookRun("benchmarking_run_nvidiadl_ssd", opts)
