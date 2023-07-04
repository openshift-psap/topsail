import time, sys, sched, yaml
import subprocess as sp
import numpy as np

scheduler = sys.argv[1]

def run_pod(n, scheduler_name):
    pod_config = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": f"test-pod-{scheduler_name}-n{n}",
        },
        "spec": {
            "containers": [
                {
                    "name": "test",
                    "image": "registry.access.redhat.com/ubi8/ubi",
                    "command": ["echo", "UBI Started"],
                },
            ],
            "restartPolicy": "Never",
        },
    }

    if scheduler == "trimaran":
        pod_config["spec"]["schedulerName"] = "trimaran-scheduler"

    yaml_pod_config = yaml.dump(pod_config, default_flow_style=False)
    start_command = ["oc", "apply", "-n", "load-aware", "-f", "-"]
    print(f"launching workload n{n} at {time.time()}")
    p = sp.run(start_command, input=yaml_pod_config.encode(), stdout=sp.PIPE)
    

times = list(map(float, sys.stdin.read().split(",")))

s = sched.scheduler(time.monotonic, time.sleep)

for i, t in enumerate(times):
    print(f"adding n{i} to the schedule at delay={t}")
    s.enter(t, 1, run_pod, argument=(i, scheduler))

print(f"running schedule at {time.time()}")
s.run()
