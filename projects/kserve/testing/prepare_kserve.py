import pathlib
import os
import logging
import time

from projects.core.library import env, config, run, sizing
from projects.rhods.library import prepare_rhoai

import test_scale

PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))

def enable_user_workload_monitoring():
    run.run(""" \
    cat <<EOF | oc apply -f-
apiVersion: v1
kind: ConfigMap
metadata:
  name: user-workload-monitoring-config
  namespace: openshift-user-workload-monitoring
data:
  config.yaml: |
    prometheus:
      logLevel: debug
      retention: 15d #Change as needed
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-monitoring-config
  namespace: openshift-monitoring
data:
  config.yaml: |
    enableUserWorkload: true
EOF
""")



def enable_kserve_raw_deployment():
    run.run("""
    new_deploy_value=$(oc get configmap/inferenceservice-config -n redhat-ods-applications  -ojsonpath={.data.deploy} | jq '.defaultDeploymentMode = "RawDeployment"');
    oc set data configmap/inferenceservice-config -n redhat-ods-applications deploy="$new_deploy_value"
    """)

    run.run("""
    new_ingress_value=$(oc get configmap/inferenceservice-config -n redhat-ods-applications  -ojsonpath={.data.ingress} | jq '.ingressClassName = "openshift-default"');
    oc set data configmap/inferenceservice-config -n redhat-ods-applications ingress="$new_ingress_value";
    """)


def customize_rhods():
    if not config.project.get_config("rhods.operator.stop"):
        return

    run.run("oc scale deploy/rhods-operator --replicas=0 -n redhat-ods-operator")
    tries = 60
    while True:
        if not run.run("oc get pods -n redhat-ods-operator -lname=rhods-operator -oname", capture_stdout=True).stdout:
            break
        tries -= 1
        if tries == 0:
            raise RuntimeError("RHODS Operator pod didn't disappear ...")
        time.sleep(2)

    if config.project.get_config("rhods.operator.customize.kserve.enabled"):
        cpu = config.project.get_config("rhods.operator.customize.kserve.cpu")
        mem = config.project.get_config("rhods.operator.customize.kserve.memory")
        run.run(f"oc get deploy/kserve-controller-manager -n redhat-ods-applications -ojson "
                f"| jq --arg mem '{mem}' --arg cpu '{cpu}' '.spec.template.spec.containers[0].resources.limits.cpu = $cpu | .spec.template.spec.containers[0].resources.limits.memory = $mem' "
                f"| oc apply -f-")
        run.run(f"oc get deploy/kserve-controller-manager -n redhat-ods-applications -oyaml > {env.ARTIFACT_DIR}/deploy_kserve-controller-manager.customized.yaml")


def customize_kserve():
    if config.project.get_config("kserve.customize.serverless.enabled"):
        egress_mem = config.project.get_config("kserve.customize.serverless.egress.limits.memory")
        ingress_mem = config.project.get_config("kserve.customize.serverless.ingress.limits.memory")
        run.run(f"oc get smcp/data-science-smcp -n istio-system -ojson "
                f"| jq --arg egress_mem '{egress_mem}' --arg ingress_mem '{ingress_mem}' "
                "'.spec.gateways.egress.runtime.container.resources.limits.memory = $egress_mem | .spec.gateways.ingress.runtime.container.resources.limits.memory = $ingress_mem' "
                f"| oc apply -f-")
        run.run(f"oc get smcp/data-science-smcp -n istio-system -oyaml > {env.ARTIFACT_DIR}/smcp_minimal.customized.yaml")


def dsc_enable_kserve():
    extra_settings = {}
    if config.project.get_config("kserve.raw_deployment.enabled"):
        extra_settings["spec.components.kserve.serving.managementState"] = "Removed"

    has_dsc = run.run("oc get dsc -oname", capture_stdout=True).stdout
    run.run_toolbox("rhods", "update_datasciencecluster",
                    enable=["kserve", "dashboard"],
                    name=None if has_dsc else "default-dsc",
                    extra_settings=extra_settings,
                    )


def prepare():
    if not PSAP_ODS_SECRET_PATH.exists():
        raise RuntimeError(f"Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")

    token_file = PSAP_ODS_SECRET_PATH / config.project.get_config("secrets.rhoai_token_file")

    if not config.project.get_config("kserve.raw_deployment.enabled"):
        with run.Parallel("prepare_kserve") as parallel:
            for operator in config.project.get_config("prepare.operators"):
                parallel.delayed(run.run_toolbox, "cluster", "deploy_operator",
                                 catalog=operator['catalog'],
                                 manifest_name=operator['name'],
                                 namespace=operator['namespace'],
                                 artifact_dir_suffix=operator['name'])

    prepare_rhoai.install(token_file)

    dsc_enable_kserve()

    if not config.project.get_config("kserve.raw_deployment.enabled"):
        with env.NextArtifactDir("prepare_poc"):
            try:
                run.run(f"projects/kserve/testing/poc/prepare.sh |& tee -a {env.ARTIFACT_DIR}/run.log")
            finally:
                run.run(f"oc get datasciencecluster -oyaml > {env.ARTIFACT_DIR}/datasciencecluster.after.yaml")

    enable_user_workload_monitoring()
    customize_rhods()
    customize_kserve()

    if config.project.get_config("kserve.raw_deployment.enabled"):
        enable_kserve_raw_deployment()


def undeploy_operator(operator, mute=True):
    manifest_name = operator["name"]
    namespace = operator["namespace"]
    if namespace == "all":
        namespace = "openshift-operators"

    cleanup = operator.get("cleanup", dict(crds=[], namespaces=[]))

    for crd in cleanup.get("crds", []):
        run.run(f"oc delete {crd} --all -A", check=False)

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
    prepare_rhoai.uninstall(mute)

    if not config.project.get_config("kserve.raw_deployment.enabled"):
        with run.Parallel("cleanup_kserve") as parallel:
            for operator in config.project.get_config("prepare.operators"):
                undeploy_operator(operator)


def update_serving_runtime_images(runtime=None):
    if runtime == "vllm":
        TEMPLATE_NAME = "vllm-runtime-template"
    else:
        TEMPLATE_NAME  = "tgis-grpc-serving-template"

    TEMPLATE_CMD = f"oc get template/{TEMPLATE_NAME} -n redhat-ods-applications"

    logging.info("Ensure that the Dashboard template resource is available ...")
    try:
        run.run(TEMPLATE_CMD, capture_stdout=True)
    except Exception:
        logging.error("update_serving_runtime_images: failed to get the dashboard templates ...")
        raise

    def get_image(name):
        cmd = f"""{TEMPLATE_CMD} -ojson | jq --arg name "{name}" '.objects[0].spec.containers[] | select(.name == $name).image' -r"""
        return run.run(cmd, capture_stdout=True).stdout

    kserve_image = get_image("kserve-container")
    #transformer_image = get_image("transformer-container")

    config.project.set_config("kserve.model.serving_runtime.kserve.image", kserve_image.strip())
    #config.project.set_config("kserve.model.serving_runtime.transformer.image", transformer_image.strip())


def preload_image():
    if config.project.get_config("clusters.sutest.is_metal"):
        return

    if not config.project.get_config("clusters.sutest.compute.dedicated"):
        return

    # this is required to properly create the namespace used to preload the image
    namespace = config.get_command_arg("cluster", "preload_image", "namespace", prefix="sutest", suffix="kserve-runtime")
    test_scale.prepare_user_sutest_namespace(namespace)

    def preload(image, name):
        RETRIES = 3
        extra = dict(image=image, name=name)

        for i in range(RETRIES):
            try:
                run.run_toolbox_from_config("cluster", "preload_image", prefix="sutest", suffix="kserve-runtime", extra=extra)

                break
            except Exception:
                logging.warning(f"Preloading of '{image}' try #{i+1}/{RETRIES} failed :/")
                if i+1 == RETRIES:
                    raise

    with run.Parallel("preload_serving_runtime") as parallel:
        parallel.delayed(preload, config.project.get_config("kserve.model.serving_runtime.kserve.image"), "kserve")
        #if not config.project.get_config("kserve.raw_deployment.enabled"):
        #    parallel.delayed(preload, config.project.get_config("kserve.model.serving_runtime.transformer.image"), "transformer")
