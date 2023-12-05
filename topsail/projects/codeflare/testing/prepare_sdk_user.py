import logging
import pathlib

from topsail.testing import env, config, run
import prepare_odh, prepare_common, prepare_gpu, prepare_user_pods


def prepare():
    """
    Prepares the cluster and the namespace for running the Codeflare-SDK user test
    """

    prepare_common.prepare_common()

    namespace = config.ci_artifacts.get_config("tests.sdk_user.namespace")
    config.ci_artifacts.set_config("base_image.namespace", namespace)
    prepare_user_pods.prepare_user_pods()

    prepare_sutest_scale_up()

    prepare_user_namespace()

    run.run_toolbox_from_config("cluster preload_image", prefix="sutest", suffix="sdk_user")


def cleanup_cluster():
    """
    Restores the cluster to its original state
    """
    prepare_common.cleanup_cluster_common()

    prepare_base_image_container()


###

import prepare_user_pods

def prepare_sutest_scale_up():
    if config.ci_artifacts.get_config("clusters.sutest.is_metal"):
        return

    node_count = prepare_user_pods.compute_node_requirement(
        cpu = config.ci_artifacts.get_config("tests.sdk_user.ray_cluster.cpu"),
        memory = config.ci_artifacts.get_config("tests.sdk_user.ray_cluster.memory"),
        machine_type = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.type"),
        user_count = config.ci_artifacts.get_config("tests.sdk_user.user_count"),
    )

    extra = {}
    extra["scale"] = node_count

    run.run_toolbox_from_config("cluster", "set_scale", prefix="sutest", extra=extra)


def prepare_user_namespace():
    namespace = config.ci_artifacts.get_config("tests.sdk_user.namespace")

    if run.run(f'oc get project -oname "{namespace}" 2>/dev/null', check=False).returncode != 0:
        run.run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')
    else:
        logging.warning(f"Project '{namespace}' already exists.")
        (env.ARTIFACT_DIR / "USER_PROJECT_ALREADY_EXISTS").touch()

    dedicated = "{}" if config.ci_artifacts.get_config("clusters.sutest.compute.dedicated") \
        else '{value: ""}' # delete the toleration/node-selector annotations, if it exists

    run.run_toolbox_from_config("cluster", "set_project_annotation", prefix="sutest", suffix="user_sdk_node_selector", extra=extra, mute_stdout=True)
    run.run_toolbox_from_config("cluster", "set_project_annotation", prefix="sutest", suffix="user_sdk_toleration", extra=dedicated, mute_stdout=True)
