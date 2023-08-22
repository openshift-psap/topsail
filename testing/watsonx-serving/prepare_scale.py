import logging
import pathlib
import os

from common import env, config, run, sizing, prepare_gpu_operator, prepare_user_pods, rhods

def compute_sutest_node_requirement():
    user_count = config.ci_artifacts.get_config("tests.scale.user_count")
    kwargs = dict(
        cpu = 7,
        memory = 10,
        machine_type = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.type"),
        user_count = user_count,
        )

    machine_count = sizing.main(**kwargs)

    # the sutest Pods must fit in one machine.
    return min(user_count, machine_count)


PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))

def prepare():
    """
    Prepares the cluster and the namespace for running the MCAD tests
    """

    if not PSAP_ODS_SECRET_PATH.exists():
        raise RuntimeError(f"Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")

    token_file = PSAP_ODS_SECRET_PATH / config.ci_artifacts.get_config("secrets.brew_registry_redhat_io_token_file")
    rhods.install(token_file)

    if not config.ci_artifacts.get_config("clusters.driver.is_metal"):
        node_count = compute_sutest_node_requirement()
        config.ci_artifacts.set_config("clusters.sutest.compute.machineset.count ", node_count)

        run.run(f"./run_toolbox.py from_config cluster set_scale --prefix=sutest")

    if config.ci_artifacts.get_config("tests.want_gpu"):
        prepare_gpu.prepare_gpu_operator()

    for operator in config.ci_artifacts.get_config("prepare.operators"):
        run.run(f"./run_toolbox.py cluster deploy_operator {operator['catalog']} {operator['name']} {operator['namespace']}")

    run.run("testing/watsonx-serving/poc/prepare.sh | tee -a $ARTIFACT_DIR/000_prepare_sh.log")

    namespace = config.ci_artifacts.get_config("base_image.namespace")
    prepare_user_pods.prepare_user_pods(namespace)
