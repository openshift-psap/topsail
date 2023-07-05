import time, sys, os, sched, yaml
import subprocess as sp
import numpy as np

print(os.getcwd())

scheduler = sys.argv[1]

make_pod_config = ""
test_pod_config = ""

with open("roles/load_aware/load_aware_scale_test/files/coreutils-make-pod.yaml", "r") as f:
    make_pod_config = f.read() 

with open("roles/load_aware/load_aware_scale_test/files/coreutils-test-pod.yaml", "r") as f:
    test_pod_config = f.read()

def run_pod(n, scheduler_name):
    make_pod = make_pod_config.format(n, scheduler_name)
    start_command = ["oc", "apply", "-f", "-"]
    print(f"launching make-pod n{n} at {time.time()}")
    p = sp.run(start_command, input=make_pod.encode(), stdout=sp.PIPE)
    # for now only launch the make_pod

times = list(map(float, sys.stdin.read().split(",")))

s = sched.scheduler(time.monotonic, time.sleep)

scheduler_name = "trimaran-scheduler" if scheduler == "trimaran" else "default-scheduler"

for i, t in enumerate(times):
    print(f"adding n{i} to the schedule at delay={t}")
    s.enter(t, 1, run_pod, argument=(i, scheduler_name))

print(f"running schedule at {time.time()}")
s.run()
