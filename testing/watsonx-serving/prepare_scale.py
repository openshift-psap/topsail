import logging
import pathlib

from common import env, config, run, prepare_gpu_operator

def prepare():
    """
    Prepares the cluster and the namespace for running the MCAD tests
    """

    run.run("./testing/utils/brew.registry.redhat.io/setup.sh $PSAP_ODS_SECRET_PATH/brew.registry.redhat.io.token")

    run.run(f"./run_toolbox.py from_config cluster set_scale --prefix=sutest")

    if config.ci_artifacts.get_config("tests.want_gpu"):
        prepare_gpu.prepare_gpu_operator()

    for operator in config.ci_artifacts.get_config("prepare.operators"):
        run.run(f"./run_toolbox.py cluster deploy_operator {operator['catalog']} {operator['name']} {operator['namespace']}")

    run.run("testing/watsonx-serving/poc/prepare.sh | tee -a $ARTIFACT_DIR/000_prepare_sh.log")
