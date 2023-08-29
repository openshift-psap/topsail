import pathlib
import os
import logging

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


def prepare():
    if not PSAP_ODS_SECRET_PATH.exists():
        raise RuntimeError(f"Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")

    token_file = PSAP_ODS_SECRET_PATH / config.ci_artifacts.get_config("secrets.brew_registry_redhat_io_token_file")
    rhods.install(token_file)

    with run.Parallel() as parallel:
        for operator in config.ci_artifacts.get_config("prepare.operators"):
            parallel.delayed(run.run, f"ARTIFACT_TOOLBOX_NAME_SUFFIX=_{operator['name']} ./run_toolbox.py cluster deploy_operator {operator['catalog']} {operator['name']} {operator['namespace']}")

    run.run("testing/watsonx-serving/poc/prepare.sh | tee -a $ARTIFACT_DIR/000_prepare_sh.log")


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
