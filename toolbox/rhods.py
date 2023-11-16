import sys

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration


class RHODS:
    """
    Commands relating to RHODS
    """

    @AnsibleRole("rhods_deploy_ods")
    @AnsibleMappedParams
    def deploy_ods(self, catalog_image, tag, channel="", version=""):
        """
        Deploy ODS operator from its custom catalog

        Args:
          catalog_image: Container image containing the RHODS bundle.
          tag: Catalog image tag to use to deploy RHODS.
          channel: The channel to use for the deployment. Let empty to use the default channel.
          version: The version to deploy. Let empty to install the last version available.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("rhods_wait_ods")
    @AnsibleMappedParams
    @AnsibleConstant("Comma-separated list of the RHODS images that should be awaited",
                     "images", "s2i-minimal-notebook,s2i-generic-data-science-notebook")
    def wait_ods(self):
        """
        Wait for ODS to finish its deployment
        """

        return RunAnsibleRole()

    @AnsibleRole("rhods_wait_odh")
    @AnsibleMappedParams
    def wait_odh(self, namespace="opendatahub"):
        """
        Wait for ODH to finish its deployment

        Args:
          namespace: namespace in which ODH is deployed
        """

        return RunAnsibleRole()

    @AnsibleRole("ocm_deploy_addon")
    @AnsibleConstant("Identifier of the addon that should be deployed",
                     "ocm_deploy_addon_id", "managed-odh")
    @AnsibleMappedParams
    @AnsibleSkipConfigGeneration
    def deploy_addon(self,
                     cluster_name, notification_email, wait_for_ready_state=True):
        """
        Installs the RHODS OCM addon

        Args:
          cluster_name: The name of the cluster where RHODS should be deployed.
          notification_email: The email to register for RHODS addon deployment.
          wait_for_ready_state: If true (default), will cause the role to wait until addon reports ready state. (Can time out)
        """

        addon_parameters = '[{"id":"notification-email","value":"'+notification_email+'"}]'

        return RunAnsibleRole(locals())

    @AnsibleRole("rhods_delete_ods")
    @AnsibleMappedParams
    def delete_ods(self,
                     namespace="redhat-ods-operator"):
        """
        Forces ODS operator deletion

        Args:
          namespace: Namespace where RHODS is installed.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("rhods_delete_ods")
    @AnsibleMappedParams
    def undeploy_ods(self,
                     namespace="redhat-ods-operator"):
        """
        Undeploy ODS operator

        Args:
          namespace: Namespace where RHODS is installed.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("rhods_cleanup_aws")
    @AnsibleMappedParams
    def cleanup_aws(self, openshift_installer=""):
        """
        Cleanup AWS from RHODS dangling resources

        Args:
          openshift_installer: path of the openshift_installer to use. If empty, download it.
        """

        return RunAnsibleRole()

    @AnsibleRole("cluster_prometheus_db")
    @AnsibleSkipConfigGeneration # see cluster.reset_prometheus_db
    @AnsibleConstant("", "cluster_prometheus_db_mode", "reset")
    @AnsibleConstant("", "cluster_prometheus_db_label", "deployment=prometheus")
    @AnsibleConstant("", "cluster_prometheus_db_namespace", "redhat-ods-monitoring")
    def reset_prometheus_db(self):
        """
        Resets RHODS Prometheus database, by destroying its Pod.
        """

        return RunAnsibleRole()

    @AnsibleRole("cluster_prometheus_db")
    @AnsibleSkipConfigGeneration # see cluster.reset_prometheus_db
    @AnsibleConstant("", "cluster_prometheus_db_mode", "dump")
    @AnsibleConstant("", "cluster_prometheus_db_label", "deployment=prometheus")
    @AnsibleConstant("", "cluster_prometheus_db_namespace", "redhat-ods-monitoring")
    @AnsibleConstant("", "cluster_prometheus_db_directory", "/prometheus/data")
    @AnsibleMappedParams
    def dump_prometheus_db(self, dump_name_prefix="prometheus"):
        """
        Dump Prometheus database into a file

        Args:
          name_prefix: Name prefix for the archive that will be stored.c
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("rhods_capture_state")
    @AnsibleMappedParams
    def capture_state(self):
        """
        Capture information about the cluster and the RHODS deployment
        """

        return RunAnsibleRole()

    @AnsibleRole("rhods_update_datasciencecluster")
    @AnsibleMappedParams
    def update_datasciencecluster(self,
                                  name=None,
                                  codeflare=False,
                                  dashboard=False,
                                  datasciencepipelines=False,
                                  kserve=False,
                                  modelmeshserving=False,
                                  ray=False,
                                  workbenches=False,
                                  ):
        """
        Update RHOAI datasciencecluster resource

        Args:
          name: Name of the resource to update. If none, update the first (and only) one found.

          codeflare: enables the codeflare component
          dashboard: enables the dashboard component
          datasciencepipelines: enables the datascience pipelines component
          kserve: enables the kserve component
          modelmeshserving: enables the modelmesh serving
          ray: enables the ray component
          workbenches: enables the workbenches component
        """

        return RunAnsibleRole(locals())
