#! /usr/bin/env python

import logging
logging.getLogger().setLevel(logging.INFO)

import types
import os
import pathlib
import math

MACHINES_FILE = pathlib.Path(os.path.dirname(os.path.realpath(__file__))) / "sizing.machines"

def parse_machines():
    machines = {}
    with open(MACHINES_FILE) as f:
        for _line in f.readlines():
            line = _line.strip()
            if line.startswith("# "):
                group = line.strip("# ")

            if not line or line.startswith("#"): continue

            instance, cpu, memory, price, *accel = line.split(", ")

            entry = types.SimpleNamespace()
            entry.cpu = int(cpu.split()[0])
            entry.memory = int(memory.split()[0])
            entry.price = float(price[1:])
            entry.group = group
            entry.name = instance

            machines[entry.name] = entry
    return machines

RESERVED_CPU = 2
RESERVED_MEM = 4

EXTRA_USERS = 1 # count as if there was +10% of users

MAX_POD_PER_NODE = 250 - 15 # 250 pods allocatable, 15 pods

def main(machine_type, user_count, cpu, memory):
    machines = parse_machines()

    pod_size = {"cpu": cpu, "memory": memory}

    machine_size = machines[machine_type]

    logging.info(f"Reserved cpu={RESERVED_CPU}, mem={RESERVED_MEM}")
    logging.info(f"Machine type:  {machine_type} --> {machine_size}")
    logging.info(f"Pod size: cpu={cpu}, mem={memory}Gi")
    logging.info("")

    total_cpu_count = pod_size["cpu"] * user_count
    total_memory_count = pod_size["memory"] * user_count

    machine_count_cpu = total_cpu_count / (machine_size.cpu - RESERVED_CPU)
    machine_count_memory = total_memory_count / (machine_size.memory - RESERVED_MEM)

    logging.info(f"Memory requirement: {machine_count_memory:.1f} x {machine_type}")
    logging.info(f"CPU requirement:    {machine_count_cpu:.1f} x {machine_type}")
    logging.info("")

    machine_exact_count = max([machine_count_cpu, machine_count_memory])
    machine_count = math.ceil(machine_exact_count)

    pods_per_machine = math.ceil(user_count/machine_count)

    # ensure that the expected pod/machine
    if pods_per_machine > MAX_POD_PER_NODE:
        logging.info(f"Computation gives {pods_per_machine} Pods per node on {machine_count}. "
                     f"Increasing the node count to stay below {MAX_POD_PER_NODE} pods/node.")
        pods_per_machine = MAX_POD_PER_NODE
        machine_count = math.ceil(user_count/pods_per_machine)

    logging.info(f"Provisioning {machine_count} {machine_type} machines "
                 f"for running {user_count} users with the pod size cpu={cpu}, mem={memory}")
    unallocated_cpu = machine_size.cpu - pod_size['cpu'] * pods_per_machine
    unallocated_mem = machine_size.memory - pod_size['memory'] * pods_per_machine

    logging.info(f"Expecting {pods_per_machine:d} pods per node "
                 f"({unallocated_cpu:.3f} cpu and {unallocated_mem:.2f}Gi of memory "
                 f"not allocated per node)")

    AWS_MAX_VOLUMES_PER_NODE = 26
    if "xlarge" in machine_type and pods_per_machine > AWS_MAX_VOLUMES_PER_NODE:
        logging.info(f"WARNING: if the Pods have AWS volumes, "
                     f"this configuration won't work (only {AWS_MAX_VOLUMES_PER_NODE} volumes "
                     f"per node is working)")
        logging.info("See https://docs.openshift.com/container-platform/4.12/storage/persistent_storage/persistent-storage-aws.html")
        logging.info("See https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/volume_limits.html")

    return machine_count


if __name__ == "__main__":
    import sys
    try:
        machine_type, _user_count, _cpu, _memory = sys.argv[1:]

        user_count = int(_user_count)
        cpu = float(_cpu)
        memory = float(_memory)
    except ValueError:
        logging.error(f"expected 4 arguments: `MACHINE_TYPE, USER_COUNT, CPU, MEMORY`, "
                      f"got {len(sys.argv[1:])}: {sys.argv[1:]}")
        logging.info(f"""Example:
MACHINE="Dell FC640"
USERS=1000

CPU=0.2
MEM=0.750
# or
CPU=1
MEM=4

{sys.argv[0]} "$MACHINE" "$USERS" "$CPU" "$MEM"
""")
        sys.exit(1)

    try:
        sys.exit(main(machine_type, user_count, cpu, memory)) # returns the number of nodes required
    except Exception as e:
        logging.error(f"'{' '.join(sys.argv)}' failed: {e.__class__.__name__}: {e}")
        sys.exit(0) # 0 means that an error occured
