import os
import logging
import pathlib
import base64
import yaml
import re

from topsail.testing import env, config, run, sizing

def apply_prefer_pr(pr_number=None):
    if not config.ci_artifacts.get_config("base_image.repo.ref_prefer_pr"):
        return

    if pr_number is not None:
        pass
    elif os.environ.get("OPENSHIFT_CI"):
        pr_number = os.environ.get("PULL_NUMBER")
        if not pr_number:
            logging.warning("apply_prefer_pr: OPENSHIFT_CI: base_image.repo.ref_prefer_pr is set but PULL_NUMBER is empty")
            return

    elif os.environ.get("PERFLAB_CI"):
        git_ref = os.environ.get("PERFLAB_GIT_REF")

        try:
            pr_number = int(re.compile("refs/pull/([0-9]+)/").match(git_ref).groups()[0])
        except Exception as e:
            logging.warning(f"apply_prefer_pr: PERFLAB_CI: base_image.repo.ref_prefer_pr is set but 'PERFLAB_GIT_REF={git_ref}' cannot be parsed: {e.__class__.__name__}: {e}")
            return

    elif os.environ.get("HOMELAB_CI"):
        pr_number = os.environ.get("PULL_NUMBER")

        if not pr_number:
            raise RuntimeError("apply_prefer_pr: HOMELAB_CI: base_image.repo.ref_prefer_pr is set but PULL_NUMBER is empty")
    else:
        logging.warning("apply_prefer_pr: Could not figure out the PR number. Keeping the default value.")
        return

    pr_ref = f"refs/pull/{pr_number}/merge"

    logging.info(f"Setting '{pr_ref}' as ref for building the base image")
    config.ci_artifacts.set_config("base_image.repo.ref", pr_ref)
    config.ci_artifacts.set_config("base_image.repo.tag", f"pr-{pr_number}")


def prepare_base_image_container(namespace):
    if config.ci_artifacts.get_config("base_image.repo.ref_prefer_pr"):
        delete_istags(namespace)

    istag = config.get_command_arg("cluster", "build_push_image", "_istag", prefix="base_image")

    if run.run(f"oc get istag {istag} -n {namespace} -oname 2>/dev/null", check=False).returncode == 0:
        logging.info(f"Image '{istag}' already exists in namespace '{namespace}'. Don't build it.")
    else:
        run.run_toolbox_from_config("cluster", "build_push_image", prefix="base_image")

    if not config.ci_artifacts.get_config("base_image.extend.enabled"):
        logging.info("Base image extention not enabled.")
        return

    run.run_toolbox_from_config("cluster", "build_push_image", prefix="extended_image")


def delete_istags(namespace):
    istag = config.get_command_arg("cluster", "build_push_image", "_istag", prefix="base_image")

    run.run(f"oc delete istag {istag} -n {namespace} --ignore-not-found")

    if config.ci_artifacts.get_config("base_image.extend.enabled"):
        istag = config.get_command_arg("cluster", "build_push_image", "_istag", prefix="extended_image")
        run.run(f"oc delete istag {istag} -n {namespace} --ignore-not-found")


def rebuild_driver_image(namespace, pr_number):
    apply_prefer_pr(pr_number)

    delete_istags(namespace)

    prepare_base_image_container(namespace)


def compute_driver_node_requirement(user_count):
    # must match 'roles/local_ci/local_ci_run_multi/templates/job.yaml.j2'
    kwargs = dict(
        cpu = 0.250,
        memory = 2,
        machine_type = config.ci_artifacts.get_config("clusters.driver.compute.machineset.type"),
        user_count = user_count,
        )

    return sizing.main(**kwargs)


def cluster_scale_up(namespace, user_count):
    if config.ci_artifacts.get_config("clusters.driver.is_metal"):
        return

    node_count = config.ci_artifacts.get_config("clusters.driver.compute.machineset.count")

    if node_count is None:
        node_count = compute_driver_node_requirement(user_count)

    extra = dict(scale=node_count)

    run.run_toolbox_from_config("cluster", "set_scale", prefix="driver", extra=extra, artifact_dir_suffix="_driver")

def prepare_user_pods(user_count):
    namespace = config.ci_artifacts.get_config("base_image.namespace")

    service_account = config.ci_artifacts.get_config("base_image.user.service_account")
    role = config.ci_artifacts.get_config("base_image.user.role")

    #
    # Prepare the driver namespace
    #
    if run.run(f'oc get project -oname "{namespace}" 2>/dev/null', check=False).returncode != 0:
        run.run(f"oc new-project '{namespace}' --skip-config-write >/dev/null")

    dedicated = "{}" if config.ci_artifacts.get_config("clusters.driver.compute.dedicated") \
        else '{value: ""}' # delete the toleration/node-selector annotations, if it exists

    with run.Parallel("prepare_user_pods") as parallel:

        #
        # Prepare the container image
        #

        parallel.delayed(prepare_base_image_container, namespace)

        #
        # Deploy Redis server for Pod startup synchronization
        #

        parallel.delayed(run.run_toolbox_from_config, "cluster", "deploy_redis_server")

        #
        # Deploy Minio
        #

        parallel.delayed(run.run_toolbox_from_config, "cluster", "deploy_minio_s3_server")

    #
    # Prepare the driver namespace annotations
    #

    run.run_toolbox_from_config("cluster", "set_project_annotation", prefix="driver", suffix="test_node_selector", extra=dedicated)
    run.run_toolbox_from_config("cluster", "set_project_annotation", prefix="driver", suffix="test_toleration", extra=dedicated)

    #
    # Prepare the ServiceAccount
    #

    run.run(f"oc create serviceaccount {service_account} -n {namespace} --dry-run=client -oyaml | oc apply -f-")
    run.run(f"oc adm policy add-cluster-role-to-user {role} -z {service_account} -n {namespace}")


    #
    # Prepare the Secret
    #

    secret_name = config.ci_artifacts.get_config("secrets.dir.name")
    secret_env_key = config.ci_artifacts.get_config("secrets.dir.env_key")

    secret_yaml_str = run.run(f"oc create secret generic {secret_name} --from-file=$(find ${secret_env_key}/* -maxdepth 1 -not -type d | tr '\\n' ,)/dev/null -n {namespace} --dry-run=client -oyaml", capture_stdout=True).stdout
    secret_yaml = yaml.safe_load(secret_yaml_str)
    del secret_yaml["data"]["null"]

    if (aws_cred_path := pathlib.Path(os.environ[secret_env_key]) / ".awscred").exists():
        with open(aws_cred_path, "rb") as f:
            file_content = f.read()
            base64_secret = base64.b64encode(file_content).decode("ascii")

        secret_yaml["data"][".awscred"] = base64_secret
    else:
        msg = f".awscred file doesn't exist in ${secret_env_key}"
        secret_yaml["data"]["awscred_missing"] = base64.b64encode(msg.encode("ascii")).decode("ascii")
        logging.warning(msg)

    save_and_create("secret.yaml", yaml.dump(secret_yaml), namespace, is_secret=True)

    run.run(f"oc describe secret {secret_name} -n {namespace} > {env.ARTIFACT_DIR}/secret_{secret_name}.descr")


def save_and_create(name, content, namespace, is_secret=False):
    file_path = pathlib.Path("/tmp") / name if is_secret \
        else env.ARTIFACT_DIR / "src" / name

    try:
        with open(file_path, "w") as f:
            print(content, file=f)

        with open(file_path) as f:
            run.run(f"oc apply -f- -n {namespace}", stdin_file=f)
    finally:
        if is_secret:
            file_path.unlink(missing_ok=True)


def cleanup_cluster():
    namespace = config.ci_artifacts.get_config("base_image.namespace")
    run.run(f"oc delete ns {namespace} --ignore-not-found")
