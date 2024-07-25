import pathlib
import types

possible_machines_cache = None

def get_possible_machines():
    global possible_machines_cache
    if possible_machines_cache is not None:
        return possible_machines_cache

    data = possible_machines_cache = []

    group = None
    with open(pathlib.Path(__file__).parent.parent / "data" / "machines") as f:
        for _line in f.readlines():
            line = _line.strip()
            if line.startswith("# "):
                group = line.strip("# ")

            if not line or line.startswith("#"): continue

            instance_name, cpu, memory, price, *accel = line.split(", ")

            data_entry = types.SimpleNamespace()
            data_entry.instance_name = instance_name
            data_entry.cpu = int(cpu.split()[0])
            data_entry.memory = int(memory.split()[0])
            data_entry.price = float(price[1:])
            data_entry.accel = accel
            data_entry.group = group

            data.append(data_entry)

    return data
