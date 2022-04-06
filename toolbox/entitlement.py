from toolbox._common import RunAnsibleRole


class Entitlement:
    """
    Commands relating to deployment and testing of entitlement files
    """
    @staticmethod
    def deploy(pem, pem_ca=None):
        """
        Deploys a cluster-wide entitlement key & RHSM config file
        (and optionally a YUM repo certificate) with the help of
        MachineConfig resources.

        Args:
            pem: Entitlement PEM file
            pem_ca: YUM repo certificate
        """
        opts = {"entitlement_pem": pem}

        if pem_ca is not None:
            opts["entitlement_repo_ca"] = pem_ca

        return RunAnsibleRole("entitlement_deploy", opts)

    @staticmethod
    def test_in_cluster(pem_key):
        """
        Tests a given PEM entitlement key on a cluster

        Args:
            pem_key: The PEM entitlement key to test
        """
        return RunAnsibleRole("entitlement_test_in_cluster", {"entitlement_pem": pem_key})

    @staticmethod
    def test_in_podman(pem_key):
        """
        Tests a given PEM entitlement key using a podman container

        Args:
            pem_key: The PEM entitlement key to test
        """
        return RunAnsibleRole("entitlement_test_in_podman", {"entitlement_pem": pem_key})

    @staticmethod
    def test_cluster(no_inspect=False):
        """
        Tests the cluster entitlement

        Args:
            no_inspect: Do not inspect on failure
            pem_ca: Deploy <pem_ca> CA PEM key on the cluster
        """
        opts = {}

        if no_inspect:
            print("INFO: Inspect on failure disabled.")
            opts["entitlement_inspect_on_failure"] = "no"

        return RunAnsibleRole("entitlement_test_wait_deployment", opts)

    @staticmethod
    def inspect():
        """
        Inspects the cluster entitlement
        """
        return RunAnsibleRole("entitlement_inspect")

    @staticmethod
    def undeploy():
        """
        Undeploys entitlement from cluster
        """
        return RunAnsibleRole("entitlement_undeploy")

    @staticmethod
    def wait():
        """
        Waits for entitlement to be deployed
        """
        opts = {
            "entitlement_test_and_wait": "yes"
        }

        return RunAnsibleRole("entitlement_wait", opts)
