import logging
import pathlib

from topsail.testing import env, config, run


def prepare_gpu_operator():
    run.run_toolbox("nfd_operator", "deploy_from_operatorhub")
    run.run_toolbox("gpu_operator", "deploy_from_operatorhub")
    run.run_toolbox_from_config("gpu_operator", "enable_time_sharing")


def cleanup_gpu_operator():
    if run.run(f'oc get project -oname nvidia-gpu-operator 2>/dev/null', check=False).returncode != 0:
        run.run("oc delete ns nvidia-gpu-operator")
        run.run("oc delete clusterpolicy --all")

    if run.run(f'oc get project -oname openshift-nfd 2>/dev/null', check=False).returncode != 0:
        run.run("oc delete ns openshift-nfd")
