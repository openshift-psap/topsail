def _generate_pod_event_times(user_count, instance_count, container_size, instance_cpu, instance_memory):
    event_times = defaultdict(types.SimpleNamespace)
    notebook_hostnames = {}


    POD_CREATION = 5
    PULL_TIME_COLD = 120
    PULL_TIME_HOT = 10
    POD_INITIALIZATION = 15
    NOTEBOOK_EXECUTION_TIME = 5*60

    def find_node():
        for node in nodes:
            if node.cpu < notebook_rq.cpu or node.memory < notebook_rq.memory:
                continue
            node.cpu -= notebook_rq.cpu
            node.memory -= notebook_rq.memory

            return node
        return None

    def reset_nodes():
        for node in nodes:
            node.cpu = instance_cpu
            node.memory = instance_memory

    def add_time(evt, previous, current, timespan_seconds):
        prev = evt.__dict__[previous]
        evt.__dict__[current] = prev + datetime.timedelta(seconds=timespan_seconds)

    users = list(range(user_count))
    nodes = [types.SimpleNamespace(idx=instance_idx, cpu=instance_cpu, memory=instance_memory)
             for instance_idx in range(instance_count)]

    notebook_rq = NOTEBOOK_REQUESTS[container_size]
    print(f"{user_count} users using {instance_count} x {{ {instance_cpu} CPUS ; {instance_memory} GB of RAM }} instances, requesting {notebook_rq.cpu} CPUs & {notebook_rq.memory} GB of RAM per notebook")

    job_creation_time = current_time = datetime.datetime.now()

    execution_round = 0
    while users:
        users_scheduled = []
        current_end = None

        for user_idx in users:
            podname = f"{JUPYTER_USER_RENAME_PREFIX}{user_idx}"
            if "warnings" not in event_times[podname].__dict__:
                event_times[podname].warnings = []

            node = find_node()

            if not node:
                if not event_times[podname].warnings:
                    event_times[podname].warnings.append(["FailedScheduling",
                                                          current_time, None,
                                                          "no node available"])
                continue

            if event_times[podname].warnings:
                event_times[podname].warnings[-1][2] = current_time

            notebook_hostnames[user_idx] = f"Node {node.idx}"

            event_times[podname].scheduled = current_time
            add_time(event_times[podname], "scheduled", "pulling", POD_CREATION)
            add_time(event_times[podname], "pulling", "pulled", PULL_TIME_COLD if execution_round == 0 else PULL_TIME_HOT)
            add_time(event_times[podname], "pulled", "started", POD_INITIALIZATION)
            add_time(event_times[podname], "started", "terminated", NOTEBOOK_EXECUTION_TIME)

            users_scheduled.append(user_idx)
            current_end = event_times[podname].terminated

        for user_idx in users_scheduled:
            users.remove(user_idx)

        if users and not users_scheduled:
            print("No user could be scheduled :(")
            break

        execution_round += 1
        current_time = current_end
        reset_nodes()

    job_completion_time = current_time

    return event_times, notebook_hostnames, job_creation_time, job_completion_time, execution_round


def _generate_timeline_results(entry, user_count, instance_count=None):
    if instance_count is None:
        instance_count = entry.import_settings["instance_count"]

    results = types.SimpleNamespace()

    results.testpod_hostnames = {user_idx: "Node {user_idx}" for user_idx in range(user_count)}
    results.notebook_hostnames = {user_idx: f"Node {user_idx}" for user_idx in range(user_count)}

    results.pod_times = {}
    results.test_pods = []

    results.ods_ci_output = {}

    results.test_pods = []
    results.job_creation_time = datetime.datetime.now()
    results.job_completion_time = datetime.datetime.now() + datetime.timedelta(minutes=5)

    times = _generate_pod_event_times(user_count,
                                      instance_count,
                                      "default",
                                      entry.results.cpu, entry.results.memory)

    results.event_times, \
        results.notebook_hostnames, \
        results.job_creation_time, \
        results.job_completion_time, \
        results.execution_round  = times

    results.notebook_pods = list(results.event_times.keys())

    return results


def _populate_theoretical_data():
    for pod_size in NOTEBOOK_REQUESTS:
        common.Matrix.settings["notebook_size"].add(pod_size)

    group = None
    with open("data/machines") as f:
        for _line in f.readlines():
            line = _line.strip()
            if line.startswith("# "):
                group = line.strip("# ")

            if not line or line.startswith("#"): continue

            instance, cpu, memory, price, *accel = line.split(", ")

            results = types.SimpleNamespace()
            results.cpu = int(cpu.split()[0])
            results.memory = int(memory.split()[0])
            results.price = float(price[1:])
            results.group = group
            import_settings = {
                "expe": "theoretical",
                "instance": instance,
            }

            store.add_to_matrix(import_settings, None, results, None)
