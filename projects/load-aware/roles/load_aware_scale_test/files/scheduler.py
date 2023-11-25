import time, sys, os, sched, yaml
import subprocess as sp
import numpy as np

print(os.getcwd())

scheduler = sys.argv[1]
namespace = sys.argv[2]
plan_file = sys.argv[3]
execution_file = sys.argv[4]
sleep_duration = sys.argv[5]

make_pod_config = ""
test_pod_config = ""
pod_configs = {}
with open("projects/load-aware/roles/load_aware_scale_test/files/coreutils-make-pod.yaml", "r") as f:
    pod_configs["make"] = f.read()

with open("projects/load-aware/roles/load_aware_scale_test/files/coreutils-test-pod.yaml", "r") as f:
    pod_configs["test"] = f.read()

with open("projects/load-aware/roles/load_aware_scale_test/files/sleep-pod.yaml", "r") as f:
    pod_configs["sleep"] = f.read()

def run_pod(n, scheduler_name, workload_name):
    # Note: the the sleep_duration argument is only present in the sleep pod
    pod = pod_configs[workload_name].format(n, scheduler_name, sleep_duration)
    start_command = ["oc", "apply", "-n", namespace, "-f", "-"]
    execution_times[n] = time.time()
    launch_make_pod_process = sp.run(start_command, input=pod.encode(), stdout=sp.PIPE)
    # for now only launch the make_pod

execution_times = {}

schedule_times = []

with open(plan_file, "r") as plan_yaml:
    schedule_times = yaml.safe_load(plan_yaml)

s = sched.scheduler(time.monotonic, time.sleep)

scheduler_name = "trimaran-scheduler" if scheduler == "trimaran" else "default-scheduler"

for i, event in enumerate(schedule_times):
    print(f"adding n{i} to the schedule at {event}")
    s.enter(event["time"], 1, run_pod, argument=(i, scheduler_name, event["workload"]))

print(f"running schedule at {time.time()}")
s.run()

with open(execution_file, "w") as execution_yaml:
    yaml.dump(execution_times, execution_yaml)
