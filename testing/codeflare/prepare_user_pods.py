import logging
import os

from common import env, config, run
  
def apply_prefer_pr():
    if not config.ci_artifacts.get_config("base_image.repo.ref_prefer_pr"):
        return

    pr_number = None

    if os.environ.get("OPENSHIFT_CI"):
        pr_number = os.environ.get("PULL_NUMBER")
        if not pr_number:
            logging.warning("apply_prefer_pr: OPENSHIFT_CI: base_image.repo.ref_prefer_pr is set but PULL_NUMBER is empty")
            return

    if os.environ.get("PERFLAB_CI"):
        git_ref = os.environ.get("PERFLAB_GIT_REF")

        try:
            pr_number = int(re.compile("refs/pull/([0-9]+)/head").match(git_ref).groups()[0])
        except Exception as e:
            logging.warning("apply_prefer_pr: PERFLAB_CI: base_image.repo.ref_prefer_pr is set cannot parse PERFLAB_GIT_REF={git_erf}: {e.__class__.__name__}: {e}")
            return

    if not pr_number:
        logging.warning("apply_prefer_pr: Could not figure out the PR number. Keeping the default value.")
        return

    pr_ref = f"refs/pull/{pr_number}/head"

    logging.info(f"Setting '{pr_ref}' as ref for building the base image")
    config.ci_artifacts.set_config("base_image.repo.ref", pr_ref)
    config.ci_artifacts.set_config("base_image.repo.tag", f"pr-{pr_number}")


def prepare_base_image_container(namespace):    
    istag = config.get_command_arg("utils build_push_image --prefix base_image", "_istag")

    if run.run(f"oc get istag {istag} -n {namespace} -oname 2>/dev/null", check=False).returncode == 0:
        logging.info(f"Image '{istag}' already exists in namespace '{namespace}'. Don't build it.")
    else:
        run.run(f"./run_toolbox.py from_config utils build_push_image --prefix base_image")

        
def prepare_user_pods(namespace):
    config.ci_artifacts.set_config("base_image.namespace", namespace)

    #
    # Prepare the container image
    #
    
    apply_prefer_pr()

    prepare_base_image_container(namespace)

    #
    # Deploy Redis server for Pod startup synchronization
    #

    run.run("./run_toolbox.py from_config cluster deploy_redis_server")

    #
    # Deploy Minio
    #

    run.run(f"./run_toolbox.py from_config cluster deploy_minio_s3_server")
    
    #
    # Prepare the Secret
    #

    secret_name = config.ci_artifacts.get_config("secrets.dir.name")
    secret_env_key = config.ci_artifacts.get_config("secrets.dir.env_key")

    run.run(f"oc create secret generic {secret_name} --from-file=$(echo ${secret_env_key}/* | tr ' ' ,) -n {namespace} --dry-run=client -oyaml | oc apply -f-")
