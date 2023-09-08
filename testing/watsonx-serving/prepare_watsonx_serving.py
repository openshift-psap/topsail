import pathlib
import os
import logging
import time

from common import env, config, run, rhods, sizing
import test_scale

PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))

def compute_sutest_node_requirement():
    ns_count = config.ci_artifacts.get_config("tests.scale.namespace_count")
    models_per_ns = config.ci_artifacts.get_config("tests.scale.models_per_namespace")
    models_count = ns_count * models_per_ns

    cpu_rq = config.ci_artifacts.get_config("watsonx_serving.serving_runtime.resource_request.cpu")
    mem_rq = config.ci_artifacts.get_config("watsonx_serving.serving_runtime.resource_request.memory")

    kwargs = dict(
        cpu = cpu_rq,
        memory = mem_rq,
        machine_type = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.type"),
        user_count = models_count,
        )

    machine_count = sizing.main(**kwargs)

    # the sutest Pods must fit in one machine.
    return min(models_count, machine_count)


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
        run.run("oc get deploy/kserve-controller-manager -n redhat-ods-applications -oyaml > $ARTIFACT_DIR/deploy_kserve-controller-manager.customized.yaml")


def customize_watsonx_serving():

    if config.ci_artifacts.get_config("watsonx_serving.customize.serverless.enabled"):
        cpu = config.ci_artifacts.get_config("watsonx_serving.customize.serverless.pilot.limits.cpu")
        mem = config.ci_artifacts.get_config("watsonx_serving.customize.serverless.pilot.limits.memory")
        run.run(f"oc get smcp/minimal -n istio-system -ojson "
                f"| jq --arg mem '{mem}' --arg cpu '{cpu}'"
                "'.spec.runtime.components.pilot.container.resources.limits.cpu = $cpu | "
                ".spec.runtime.components.pilot.container.resources.limits.memory = $mem' "
                f"| oc apply -f-")
        run.run("oc get smcp/minimal -n istio-system -oyaml > $ARTIFACT_DIR/smcp_minimal.customized.yaml")

def prepare():
    if not PSAP_ODS_SECRET_PATH.exists():
        raise RuntimeError(f"Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")

    token_file = PSAP_ODS_SECRET_PATH / config.ci_artifacts.get_config("secrets.brew_registry_redhat_io_token_file")

    with run.Parallel("prepare_watsonx_serving") as parallel:
        parallel.delayed(rhods.install, token_file)

        for operator in config.ci_artifacts.get_config("prepare.operators"):
            parallel.delayed(run.run, f"ARTIFACT_TOOLBOX_NAME_SUFFIX=_{operator['name']} ./run_toolbox.py cluster deploy_operator {operator['catalog']} {operator['name']} {operator['namespace']}")

    run.run("testing/watsonx-serving/poc/prepare.sh |& tee -a $ARTIFACT_DIR/000_prepare_sh.log")

    customize_rhods()
    customize_watsonx_serving()


def scale_up_sutest():
    if config.ci_artifacts.get_config("clusters.sutest.is_metal"):
        return

    node_count = compute_sutest_node_requirement()
    config.ci_artifacts.set_config("clusters.sutest.compute.machineset.count ", node_count)

    run.run(f"ARTIFACT_TOOLBOX_NAME_SUFFIX=_sutest ./run_toolbox.py from_config cluster set_scale --prefix=sutest")


def preload_image():
    if config.ci_artifacts.get_config("clusters.sutest.is_metal"):
        return

    if not config.ci_artifacts.get_config("clusters.sutest.compute.dedicated"):
        return

    # this is required to properly create the namespace used to preload the image
    test_namespace = config.ci_artifacts.get_config("tests.scale.namespace")
    test_scale.prepare_user_namespace(test_namespace)

    RETRIES = 3
    for i in range(RETRIES):
        try:
            run.run("./run_toolbox.py from_config cluster preload_image --prefix sutest --suffix watsonx-serving-runtime")
            break
        except Exception:
            logging.warning("Watsonx Serving Runtime image preloading try #{i}/{RETRIES} failed :/")
            if i == RETRIES:
                raise
