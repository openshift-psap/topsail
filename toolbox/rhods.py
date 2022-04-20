import sys

from toolbox._common import RunAnsibleRole


class RHODS:
    """
    Commands relating to RHODS
    """

    @staticmethod
    def deploy_ods():
        """
        Deploy ODS operator from its custom catalog
        """

        return RunAnsibleRole("rhods_deploy_ods")

    @staticmethod
    def deploy_ldap(username_prefix, username_count: int, secret_properties_file):
        """
        Deploy OpenLDAP and LDAP Oauth

        Example of secret properties file:

        user_password=passwd
        admin_password=adminpasswd

        Args:
            username_prefix: Prefix for the creation of the users (suffix is 0..username_count)
            username_count: Number of users to create.
            secret_properties_file: Path of a file containing the properties of LDAP secrets.
        """

        opts = {
            "rhods_deploy_ldap_username_prefix": username_prefix,
            "rhods_deploy_ldap_username_count": username_count,
            "rhods_deploy_ldap_secret_properties": secret_properties_file,
        }

        return RunAnsibleRole("rhods_deploy_ldap", opts)
