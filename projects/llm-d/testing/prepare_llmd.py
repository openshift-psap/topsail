#!/usr/bin/env python

import pathlib
import logging
import datetime
import time
import uuid
import os

import yaml

from projects.core.library import env, config, run

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))

def prepare():
    """
    Prepares the cluster for LLM-D testing
    """

    if config.project.get_config("prepare.skip"):
        logging.info("Preparation skipped")
        return

    prepare_operators()
    prepare_monitoring()
    prepare_grafana()
    prepare_gpu()
    prepare_rhoai()
    prepare_gateway()
    prepare_namespace()


def prepare_operators():
    """
    Prepares operators defined in the configuration
    """

    if config.project.get_config("prepare.operators.skip"):
        logging.info("Operators preparation skipped")
        return

    operators_list = config.project.get_config("prepare.operators.list")
    if not operators_list:
        logging.info("No operators to deploy")
        return

    logging.info("Preparing operators")

    for operator_config in operators_list:
        deploy_operator(operator_config)


def deploy_operator(operator_config):
    """
    Deploys a single operator based on configuration
    """

    name = operator_config.get("name")
    catalog = operator_config.get("catalog", "redhat-operators")
    operator = operator_config.get("operator")
    namespace = operator_config.get("namespace", "all")
    deploy_cr = operator_config.get("deploy_cr", False)
    enabled = operator_config.get("enabled", True)

    if not enabled:
        logging.info(f"Skipping disabled operator: {name}")
        return

    if not operator:
        logging.error(f"Operator configuration missing 'operator' field: {operator_config}")
        return

    logging.info(f"Deploying operator: {name}")

    # Build the arguments dictionary
    args_dict = {
        "catalog": catalog,
        "manifest_name": operator,
        "namespace": namespace,
    }

    if deploy_cr is not None:
        args_dict["deploy_cr"] = True if deploy_cr is True else \
            str(deploy_cr)

    # Add any extra arguments
    extra_args = operator_config.get("extra_args", {})
    if extra_args:
        args_dict.update(extra_args)

    run.run_toolbox("cluster", "deploy_operator", **args_dict)
    logging.info(f"Successfully deployed operator: {name}")


def prepare_grafana():
    """
    Prepares Grafana resources (datasources and dashboards)
    """

    if config.project.get_config("prepare.grafana.skip"):
        logging.info("Grafana preparation skipped")
        return

    logging.info("Preparing Grafana resources")

    # Deploy Grafana datasources
    datasources = config.project.get_config("prepare.grafana.datasources")
    for datasource_path in datasources or []:
        datasource_file = TESTING_THIS_DIR / datasource_path
        if not datasource_file.exists():
            logging.warning(f"Grafana datasource file not found: {datasource_file}")
            continue

        logging.info(f"Deploying Grafana datasource: {datasource_path}")
        run.run(f"oc apply -f {datasource_file}")

    # Deploy Grafana dashboards
    dashboards_dir_path = config.project.get_config("prepare.grafana.dashboards_dir")
    if dashboards_dir_path:
        dashboards_dir = TESTING_THIS_DIR / dashboards_dir_path
        dashboard_files = list(dashboards_dir.glob("*.yaml"))
        logging.info(f"Deploying {len(dashboard_files)} Grafana dashboard(s) from {dashboards_dir_path}")
        for dashboard_file in dashboard_files:
            logging.info(f"  - {dashboard_file.name}")
            run.run(f"oc apply -f {dashboard_file}")
    else:
        logging.info("No Grafana dashboards directory configured")


def prepare_monitoring():
    """
    Prepares cluster monitoring (user workload monitoring)
    """

    if config.project.get_config("prepare.monitoring.skip"):
        logging.info("Monitoring preparation skipped")
        return

    logging.info("Preparing cluster monitoring")

    # Get namespaces to enable monitoring for
    monitored_namespaces = config.project.get_config("prepare.monitoring.namespaces")
    for i, ns in enumerate(monitored_namespaces):
        # we fetch the *list*, so the references aren't resolved in 'get_config',
        # eg: ['@prepare.namespace.name']
        monitored_namespaces[i] = config.project.resolve_reference(ns)

    # Enable user workload monitoring
    run.run_toolbox("cluster", "enable_userworkload_monitoring",
                    namespaces=monitored_namespaces or [])

    logging.info("Cluster monitoring setup completed successfully")


def prepare_gpu():
    """
    Prepares the cluster for GPU operations
    """

    if config.project.get_config("prepare.gpu.skip"):
        logging.info("GPU preparation skipped")
        return

    logging.info("Preparing cluster for GPU operations")

    # Scale up the cluster if configured
    gpu_instance_type = config.project.get_config("prepare.gpu.instance_type")
    gpu_count = config.project.get_config("prepare.gpu.count")

    if gpu_instance_type and gpu_count:
        logging.info(f"Scaling cluster to {gpu_count} {gpu_instance_type} instances")
        run.run_toolbox("cluster", "set_scale",
                       instance_type=gpu_instance_type,
                       scale=str(gpu_count))

    # Wait for GPU nodes to be ready
    run.run_toolbox("nfd", "wait_gpu_nodes")
    run.run_toolbox("gpu-operator", "wait_stack_deployed")


def prepare_rhoai():
    """
    Prepares RHOAI (Red Hat OpenShift AI)
    """

    if config.project.get_config("prepare.rhoai.skip"):
        logging.info("RHOAI preparation skipped")
        return

    logging.info("Preparing RHOAI")

    # Apply pre-release registry token if available
    if PSAP_ODS_SECRET_PATH.exists() and (PSAP_ODS_SECRET_PATH / "rhoai-quay.sh").exists():
        logging.info("Applying pre-release image registry token")
        run.run(f"bash {PSAP_ODS_SECRET_PATH / 'rhoai-quay.sh'}")

        # Apply ImageContentSourcePolicy for quay registry
        icsp_yaml = """
apiVersion: operator.openshift.io/v1alpha1
kind: ImageContentSourcePolicy
metadata:
  name: quay-registry
spec:
  repositoryDigestMirrors:
    - source: registry.redhat.io/rhoai
      mirrors:
        - quay.io/rhoai
"""
        run.run(f"oc apply -f-", input=icsp_yaml)

    # Deploy RHOAI
    rhoai_image = config.project.get_config("prepare.rhoai.image")
    rhoai_tag = config.project.get_config("prepare.rhoai.tag")
    rhoai_channel = config.project.get_config("prepare.rhoai.channel")

    run.run_toolbox("rhods", "deploy_ods",
                   image=rhoai_image,
                   tag=rhoai_tag,
                   channel=rhoai_channel)

    # Enable KServe
    enable_components = config.project.get_config("prepare.rhoai.datasciencecluster.enable")
    extra_settings = config.project.get_config("prepare.rhoai.datasciencecluster.extra_settings")

    run.run_toolbox("rhods", "update_datasciencecluster",
                   enable=enable_components,
                   extra_settings=extra_settings)


def prepare_gateway():
    """
    Prepares the Gateway for LLM inference
    """

    if config.project.get_config("prepare.gateway.skip"):
        logging.info("Gateway preparation skipped")
        return

    logging.info("Preparing Gateway for LLM inference")

    # Get gateway name from config
    gateway_name = config.project.get_config("prepare.gateway.name")

    logging.info(f"Deploying gateway: {gateway_name}")

    run.run_toolbox("llmd", "deploy_gateway", gateway_name=gateway_name)


def prepare_namespace():
    """
    Prepares the namespace for LLM testing
    """

    namespace = config.project.get_config("prepare.namespace.name")

    logging.info(f"Preparing namespace: {namespace}")

    # Create the namespace
    run.run(f'oc new-project "{namespace}" --skip-config-write >/dev/null', check=False)

    return namespace


def cleanup_cluster():
    """
    Cleans up the cluster
    """

    if config.project.get_config("prepare.cleanup.skip"):
        logging.info("Cleanup skipped")
        return

    logging.info("Cleaning up LLM-D cluster resources")

    namespace = config.project.get_config("prepare.namespace.name")

    # Delete namespace
    try:
        run.run(f"oc delete namespace {namespace} --ignore-not-found")
    except Exception as e:
        logging.warning(f"Failed to delete namespace {namespace}: {e}")

    # Scale down cluster if configured
    gpu_instance_type = config.project.get_config("prepare.gpu.instance_type")
    if gpu_instance_type:
        try:
            run.run_toolbox("cluster", "set_scale",
                           instance_type=gpu_instance_type,
                           scale="0")
        except Exception as e:
            logging.warning(f"Failed to scale down cluster: {e}")
