import sys

from toolbox._common import PlaybookRun


class Cluster:
    """
    Commands relating to cluster scaling, upgrading and environment capture
    """
    @staticmethod
    def set_scale(instance_type, scale, base_machineset=None, force=False):
        """
        Ensures that the cluster has exactly `scale` nodes with instance_type `instance_type`

        If the machinesets of the given instance type already have the required total number of replicas,
        their replica parameters will not be modified.
        Otherwise,
        - If there's only one machineset with the given instance type, its replicas will be set to the value of this parameter.

        - If there are other machinesets with non-zero replicas, the playbook will fail, unless the 'force_scale' parameter is
        set to true. In that case, the number of replicas of the other machinesets will be zeroed before setting the replicas
        of the first machineset to the value of this parameter."

        - If `--base-machineset=machineset` flag is passed, `machineset` machineset will be used to derive the new
        machinetset (otherwise, the first machinetset of the listing will be used). This is useful if the desired `instance_type`
        is only available in some specific regions and, controlled by different machinesets.

        Example: ./run_toolbox.py cluster set_scale g4dn.xlarge 1 # ensure that the cluster has 1 GPU node

        Args:
            instance_type: The instance type to use, for example, g4dn.xlarge
            scale: The number of required nodes with given instance type
            base_machineset: Name of a machineset to use to derive the new one. Default: pickup the first machineset found in `oc get machinesets -n openshift-machine-api`.
        """
        opts = {
            "machineset_instance_type": instance_type,
            "scale": scale,
        }

        if base_machineset is not None:
            opts["base_machineset"] = base_machineset

        if force:
            opts["force_scale"] = "true"

        return PlaybookRun("cluster_set_scale", opts)

    @staticmethod
    def upgrade_to_image(image):
        """
        Upgrades the cluster to the given image

        Args:
            image: The image to upgrade the cluster to
        """
        return PlaybookRun("cluster_upgrade_to_image", {"cluster_upgrade_image": image})

    @staticmethod
    def capture_environment():
        """
        Captures the cluster environment

        Args:
            image: The image to upgrade the cluster to
        """
        return PlaybookRun("cluster_capture_environment")

    @staticmethod
    def wait_for_alert(alert_name, alert_active: bool):
        """
        Wait for an alert to be active or inactive.

        Args:
            alert_name: The name of the alert to wait for
            alert_active: A boolean telling if the alert should be active or not (true|false)
        """

        if alert_active not in ("true", "false"):
            print(f"Unexpected value for alert_active: '{alert_active}'. Expected a boolean (true|false).")
            sys.exit(1)

        opts = {
            "cluster_wait_for_alert_name": alert_name,
            "cluster_wait_for_alert_active": alert_active,
        }

        return PlaybookRun("cluster_wait_for_alert", opts)


    @staticmethod
    def deploy_operator(catalog, manifest_name, namespace, version=None, channel=None, install_plan="Manual", deploy_cr=False, ns_monitoring=False):
        """
        Deploy an operator from OperatorHub catalog entry.

        Args:
            catalog: Name of the catalog containing the operator.
            manifest_name: Name of the operator package manifest.
            namespace: Namespace in which the operator will be deployed, or 'all' to deploy in all the namespaces.
            channel: Optional channel to deploy from. If unspecified, deploys the CSV's default channel. Use '?' to list the available channels for the given package manifest.
            version: Optional version to deploy. If unspecified, deploys the latest version available in the selected channel.
            install_plan: Optional InstallPlan approval mode (Automatic or Manual). Default: Manual.
            deploy_cr: Optional boolean flag to deploy the first example CR found in the CSV.
            ns_monitoring: Optional boolean flag to enable OpenShift namespace monitoring. Default: False.
        """

        opts = {
            "cluster_deploy_operator_catalog": catalog,
            "cluster_deploy_operator_manifest_name": manifest_name,
        }


        if namespace == "all":
            opts["cluster_deploy_operator_all_namespaces"] = "True"
            opts["cluster_deploy_operator_namespace"] = "openshift-operators"
            if ns_monitoring:
                print("Namespace monitoring cannot be enabled when deploying in all the namespaces.")
                sys.exit(1)

            print(f"Deploying the operator in all the namespaces.")
        else:
            opts["cluster_deploy_operator_namespace"] = namespace
            opts["cluster_deploy_operator_namespace_monitoring"] = ns_monitoring
            if ns_monitoring:
                print(f"Enabling namespace monitoring.")

            print(f"Deploying the operator using namespace '{namespace}'.")


        if channel is not None:
            opts["cluster_deploy_operator_channel"] = channel
            print(f"Deploying the operator using channel '{channel}'.")

        if version is not None:
            if channel is None:
                print("Version may only be specified if --channel is specified")
                sys.exit(1)

            opts["cluster_deploy_operator_version"] = version
            print(f"Deploying the operator using version '{version}'.")

        opts["cluster_deploy_operator_installplan_approval"] = install_plan
        if install_plan not in ("Manual", "Automatic"):
            print(f"--install-plan can only be Manual or Automatic. Received '{install_plan}'.")
            sys.exit(1)

        print(f"Deploying the operator using InstallPlan approval mode '{install_plan}'.")

        opts["cluster_deploy_operator_deploy_cr"] = deploy_cr
        if deploy_cr:
            print(f"Deploying the operator default CR.")


        print("Deploying the operator.")

        return PlaybookRun("cluster_deploy_operator", opts)
