import os
import sys
import logging

from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams, AnsibleConstant,
    AnsibleSkipConfigGeneration
)

class Cpt:
    """
    Commands relating to continuous performance testing management
    """

    @AnsibleRole("cpt_deploy_cpt_dashboard")
    @AnsibleMappedParams
    def deploy_cpt_dashboard(self,
                             frontend_istag,
                             backend_istag,
                             plugin_name,
                             es_url,
                             es_indice,
                             es_username,
                             secret_properties_file,
                             namespace="topsail-cpt-dashboard",

                    ):
        """
        Deploy and configure the CPT Dashboard

        Example of secret properties file:

        admin_password=adminpasswd

        Args:
          namespace: namespace in which the application will be deployed

          frontend_istag: Imagestream tag to use for the frontend container
          backend_istag: Imagestream tag to use for the backend container

          plugin_name: Name of the CPT Dashboard plugin to configure

          es_url: URL of the OpenSearch backend
          es_indice: indice of the OpenSearch backend
          es_username: username to use to login into OpenSearch
          secret_properties_file: Path of a file containing the OpenSearch user credentials
        """

        return RunAnsibleRole(locals())
