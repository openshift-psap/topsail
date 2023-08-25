import logging
import pathlib

from common import env, config, run


def prepare_gpu_operator():
    run.run("./run_toolbox.py nfd_operator deploy_from_operatorhub")
    run.run("./run_toolbox.py gpu_operator deploy_from_operatorhub")
    run.run("./run_toolbox.py from_config gpu_operator enable_time_sharing")


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
