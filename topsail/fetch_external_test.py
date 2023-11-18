import os
import json

from topsail._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams

class Fetch_External_Test:
    """
    Commands relating to fetch-external-test
    """

    @AnsibleRole("fetch_external_test")
    @AnsibleMappedParams
    def run(self,
            collection,
            role,
            task,
            ):
        """
        Run an external test

        Args:
          collection: the collection to be executed
          role: the role to be executed
          task: tasks file to be executed
        """

        return RunAnsibleRole(locals())
