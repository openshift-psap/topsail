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
