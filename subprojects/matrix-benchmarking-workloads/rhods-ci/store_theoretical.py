import types

NOTEBOOK_REQUESTS = dict(
    test_pod=types.SimpleNamespace(cpu=0.2, memory=0.4),
    default=types.SimpleNamespace(cpu=1, memory=4),
    small=types.SimpleNamespace(cpu=1,   memory=8),
    medium=types.SimpleNamespace(cpu=3,  memory=24),
)

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
