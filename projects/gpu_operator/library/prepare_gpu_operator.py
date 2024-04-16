import logging
import pathlib

from projects.core.library import env, config, run


def prepare_gpu_operator():
    if run.run("oc get csv -loperators.coreos.com/nfd.openshift-nfd= -n openshift-nfd -oname", check=False, capture_stdout=True).stdout:
        logging.info("The NFD Operator is already installed.")
    else:
        run.run_toolbox("nfd_operator", "deploy_from_operatorhub")

    if run.run(f"oc get csv -loperators.coreos.com/gpu-operator-certified.nvidia-gpu-operator= -n nvidia-gpu-operator -oname", capture_stdout=True).stdout:
        logging.info("The NVIDIA GPU Operator is already installed.")
    else:
        run.run_toolbox("gpu_operator", "deploy_from_operatorhub")

def wait_ready(*, enable_time_sharing=True, extend_metrics=True, wait_metrics=True, wait_stack_deployed=True):
    if enable_time_sharing:
        run.run_toolbox_from_config("gpu_operator", "enable_time_sharing")

    if extend_metrics:
        run.run_toolbox("gpu_operator", "extend_metrics", include_defaults=True, include_well_known=True, wait_refresh=wait_metrics)

    if wait_stack_deployed:
        run.run_toolbox("gpu_operator", "wait_stack_deployed")


def cleanup_gpu_operator():
    if run.run(f'oc get project -oname nvidia-gpu-operator 2>/dev/null', check=False).returncode != 0:
        run.run("oc delete ns nvidia-gpu-operator")
        run.run("oc delete clusterpolicy --all")

    if run.run(f'oc get project -oname openshift-nfd 2>/dev/null', check=False).returncode != 0:
        run.run("oc delete ns openshift-nfd")


def add_toleration(effect, key):
    run.run("""\
    oc patch clusterpolicy/gpu-cluster-policy  \
             --type=json -p='{"spec":{"daemonsets":{"tolerations":[{"effect":\""""+effect+"""\","key":\""""+key+"""\","operator":"Exists"}]}}}' \
             --type merge""")
