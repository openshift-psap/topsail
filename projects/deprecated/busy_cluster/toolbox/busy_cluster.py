import os
import sys
import logging

from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams, AnsibleConstant,
    AnsibleSkipConfigGeneration
)

class Busy_Cluster:
    """
    Commands relating to make a cluster busy with lot of resources
    """


    @AnsibleRole("busy_cluster_create_namespaces")
    @AnsibleMappedParams
    def create_namespaces(
            self,
            prefix="busy-namespace",
            count=10,
            labels={},
    ):
        """
        Creates namespaces to make a cluster busy

        Args:
          prefix: prefix to give to the namespaces to create
          count: number of namespaces to create
          labels: dict of the key/value labels to set for the namespace
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("busy_cluster_create_configmaps")
    @AnsibleMappedParams
    def create_configmaps(
            self,
            namespace_label_key="busy-cluster.topsail",
            namespace_label_value="yes",
            prefix="busy",
            count=10,
            labels={},
            as_secrets=False,
            entries=10,
            entry_values_length=1024,
            entry_keys_prefix="entry-"
    ):
        """
        Creates configmaps and secrets to make a cluster busy

        Args:
          namespace_label_key: the label key to use to locate the namespaces to populate
          namespace_label_value: the label value to use to locate the namespaces to populate
          prefix: prefix to give to the configmaps/secrets to create
          count: number of configmaps/secrets to create
          labels: dict of the key/value labels to set for the configmap/secrets
          as_secrets: if True, creates secrets instead of configmaps

          entries: number of entries to create
          entry_keys_prefix: the prefix to use to create the entry values
          entry_values_length: length of an entry value
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("busy_cluster_create_deployments")
    @AnsibleMappedParams
    def create_deployments(
            self,
            namespace_label_key="busy-cluster.topsail",
            namespace_label_value="yes",
            prefix="busy",
            count=1,
            labels={},

            replicas=1,
            services=1,

            image_pull_back_off=False,
            crash_loop_back_off=False,
    ):
        """
        Creates configmaps and secrets to make a cluster busy

        Args:
          namespace_label_key: the label key to use to locate the namespaces to populate
          namespace_label_value: the label value to use to locate the namespaces to populate
          prefix: prefix to give to the deployments to create
          count: number of deployments to create
          labels: dict of the key/value labels to set for the deployments

          replicas: number of replicas to set for the deployments
          services: number of services to create for each of the deployments

          image_pull_back_off: if True, makes the containers image pull fail.
          crash_loop_back_off: if True, makes the containers fail. If a integer value, wait this many seconds before failing.
        """

        if image_pull_back_off and crash_loop_back_off:
            logging.fatal("Cannot use crashLoopBackOff and imagePullBackOff at the same time.")
            sys.exit(1)

        return RunAnsibleRole(locals())

    @AnsibleRole("busy_cluster_create_jobs")
    @AnsibleMappedParams
    def create_jobs(
            self,
            namespace_label_key="busy-cluster.topsail",
            namespace_label_value="yes",
            prefix="busy",
            count=10,
            labels={},

            replicas=2,
            runtime=120,
    ):
        """
        Creates jobs to make a cluster busy

        Args:
          namespace_label_key: the label key to use to locate the namespaces to populate
          namespace_label_value: the label value to use to locate the namespaces to populate
          prefix: prefix to give to the deployments to create
          count: number of deployments to create
          labels: dict of the key/value labels to set for the deployments

          replicas: the number of parallel tasks to execute
          runtime: the runtime of the Job Pods in seconds, of inf
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("busy_cluster_status")
    @AnsibleMappedParams
    def status(
            self,
            namespace_label_key="busy-cluster.topsail",
            namespace_label_value="yes",
    ):
        """
        Shows the busyness of the cluster

        Args:
          namespace_label_key: the label key to use to locate the namespaces to cleanup
          namespace_label_value: the label value to use to locate the namespaces to cleanup
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("busy_cluster_cleanup")
    @AnsibleMappedParams
    def cleanup(
            self,
            namespace_label_key="busy-cluster.topsail",
            namespace_label_value="yes",
    ):
        """
        Cleanups namespaces to make a cluster un-busy

        Args:
          namespace_label_key: the label key to use to locate the namespaces to cleanup
          namespace_label_value: the label value to use to locate the namespaces to cleanup
        """

        return RunAnsibleRole(locals())
