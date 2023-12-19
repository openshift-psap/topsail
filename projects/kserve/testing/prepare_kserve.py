import pathlib
import os
import logging
import time

from topsail.testing import env, config, run, rhods, sizing
import test_scale

PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))


def customize_rhods():
    if not config.ci_artifacts.get_config("rhods.operator.stop"):
        return

    run.run("oc scale deploy/rhods-operator --replicas=0 -n redhat-ods-operator")
    tries = 60
    while True:
        if not run.run("oc get pods -n redhat-ods-operator -lname=rhods-operator -oname", capture_stdout=True).stdout:
            break
        tries -= 1
        if tries == 0:
            raise RuntimeException("RHODS Operator pod didn't disappear ...")
        time.sleep(2)

    if config.ci_artifacts.get_config("rhods.operator.customize.kserve.enabled"):
        cpu = config.ci_artifacts.get_config("rhods.operator.customize.kserve.cpu")
        mem = config.ci_artifacts.get_config("rhods.operator.customize.kserve.memory")
        run.run(f"oc get deploy/kserve-controller-manager -n redhat-ods-applications -ojson "
                f"| jq --arg mem '{mem}' --arg cpu '{cpu}' '.spec.template.spec.containers[0].resources.limits.cpu = $cpu | .spec.template.spec.containers[0].resources.limits.memory = $mem' "
                f"| oc apply -f-")
        run.run(f"oc get deploy/kserve-controller-manager -n redhat-ods-applications -oyaml > {env.ARTIFACT_DIR}/deploy_kserve-controller-manager.customized.yaml")


def customize_kserve():

    if config.ci_artifacts.get_config("kserve.customize.serverless.enabled"):
        egress_mem = config.ci_artifacts.get_config("kserve.customize.serverless.egress.limits.memory")
        ingress_mem = config.ci_artifacts.get_config("kserve.customize.serverless.ingress.limits.memory")
        run.run(f"oc get smcp/minimal -n istio-system -ojson "
                f"| jq --arg egress_mem '{egress_mem}' --arg ingress_mem '{ingress_mem}' "
                "'.spec.gateways.egress.runtime.container.resources.limits.memory = $egress_mem | .spec.gateways.ingress.runtime.container.resources.limits.memory = $ingress_mem' "
                f"| oc apply -f-")
        run.run(f"oc get smcp/minimal -n istio-system -oyaml > {env.ARTIFACT_DIR}/smcp_minimal.customized.yaml")

def prepare():
    if not PSAP_ODS_SECRET_PATH.exists():
        raise RuntimeError(f"Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")

    token_file = PSAP_ODS_SECRET_PATH / config.ci_artifacts.get_config("secrets.brew_registry_redhat_io_token_file")

    with run.Parallel("prepare_kserve") as parallel:
        for operator in config.ci_artifacts.get_config("prepare.operators"):
            parallel.delayed(run.run_toolbox, "cluster", "deploy_operator", catalog=operator['catalog'], manifest_name=operator['name'], namespace=operator['namespace'], artifact_dir_suffix=operator['name'])

    rhods.install(token_file)

    has_dsc = run.run("oc get dsc -oname", capture_stdout=True).stdout
    run.run_toolbox("rhods", "update_datasciencecluster", enable=["kserve"],
                    name=None if has_dsc else "default-dsc")

    with env.NextArtifactDir("prepare_poc"):
        try:
            run.run(f"projects/kserve/testing/poc/prepare.sh |& tee -a {env.ARTIFACT_DIR}/run.log")
        finally:
            run.run(f"oc get datasciencecluster -oyaml > {env.ARTIFACT_DIR}/datasciencecluster.after.yaml")

    customize_rhods()
    customize_kserve()


def undeploy_operator(operator, mute=True):
    manifest_name = operator["name"]
    namespace = operator["namespace"]
    if namespace == "all":
        namespace = "openshift-operators"

    cleanup = operator.get("cleanup", dict(crds=[], namespaces=[]))

    for crd in cleanup.get("crds", []):
        run.run(f"oc delete {crd} --all -A", check=False)

    for ns in cleanup.get("namespaces", []):
        run.run(f"oc api-resources --verbs=list --namespaced -o name | grep -v -E 'coreos.com|openshift.io|cncf.io|k8s.io|metal3.io|k8s.ovn.org|.apps' | xargs -t -n 1 oc get --show-kind --ignore-not-found -n kserve-user-test-driver |& cat > {env.ARTIFACT_DIR}/{operator['name']}_{ns}.log", check=False)

    installed_csv_cmd = run.run(f"oc get csv -oname -n {namespace} -loperators.coreos.com/{manifest_name}.{namespace}", capture_stdout=mute)
    if not installed_csv_cmd.stdout:
        logging.info(f"{manifest_name} operator is not installed")

    run.run(f"oc delete sub/{manifest_name} -n {namespace} --ignore-not-found")
    run.run(f"oc delete csv -n {namespace} -loperators.coreos.com/{manifest_name}.{namespace}")

    for crd in cleanup.get("crds", []):
        run.run(f"oc delete crd/{crd} --ignore-not-found")

    for ns in cleanup.get("namespaces", []):
        run.run(f"timeout 300 oc delete ns {ns} --ignore-not-found")


def cleanup(mute=True):
    rhods.uninstall(mute)

    with run.Parallel("cleanup_kserve") as parallel:
        for operator in config.ci_artifacts.get_config("prepare.operators"):
            undeploy_operator(operator)


def preload_image():
    if config.ci_artifacts.get_config("clusters.sutest.is_metal"):
        return

    if not config.ci_artifacts.get_config("clusters.sutest.compute.dedicated"):
        return

    # this is required to properly create the namespace used to preload the image
    namespace = config.get_command_arg("cluster", "preload_image", "namespace", prefix="sutest", suffix="kserve-runtime")
    test_scale.prepare_user_sutest_namespace(namespace)

    def preload(image):
        RETRIES = 3
        extra = dict(image=image)
        for i in range(RETRIES):
            try:
                run.run_toolbox_from_config("cluster", "preload_image", prefix="sutest", suffix="kserve-runtime", extra=extra)

                break
            except Exception:
                logging.warning(f"Preloading of '{image}' try #{i+1}/{RETRIES} failed :/")
                if i+1 == RETRIES:
                    raise

    with run.Parallel("preload_serving_runtime") as parallel:
        preload(config.ci_artifacts.get_config("kserve.model.serving_runtime.kserve.image"))
        preload(config.ci_artifacts.get_config("kserve.model.serving_runtime.transformer.image"))
