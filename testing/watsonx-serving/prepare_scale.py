import logging
import pathlib

from common import env, config, run, sizing, prepare_gpu_operator, prepare_user_pods

def compute_sutest_node_requirement():
    kwargs = dict(
        cpu = 6.9,
        memory = 10,
        machine_type = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.type"),
        user_count = config.ci_artifacts.get_config("tests.scale.user_count"),
        )

    return sizing.main(**kwargs)

def prepare():
    """
    Prepares the cluster and the namespace for running the MCAD tests
    """

    run.run("./testing/utils/brew.registry.redhat.io/setup.sh $PSAP_ODS_SECRET_PATH/brew.registry.redhat.io.token")

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
