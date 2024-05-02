import types
import datetime
import json
from pathlib import PosixPath
from collections import defaultdict, OrderedDict
import logging
import pytz

from . import prom

import matrix_benchmarking.common as common

lts_metrics = {
    'sutest': []
}

def register_lts_metric(cluster_role, metric):
    for (name, query) in metric.items():
        lts_metrics[cluster_role].append((name, query))


def _recursive_create_namespace(obj: dict) -> types.SimpleNamespace:
    final_obj = {}
    for (key, val) in obj.items():
        out_val = val
        if type(val) is dict:
            out_val = _recursive_create_namespace(val)
        if type(val) is list:
            out_val = []
            for i in val:
                out_val.append(_recursive_create_namespace(i))

        final_obj[key] = out_val

    return types.SimpleNamespace(**final_obj)


def _parse_entry(val):
    type_skiplist = [PosixPath, types.FunctionType]

    val_type = type(val)

    if val_type is datetime.datetime:
        return datetime.datetime.timestamp(val)

    elif val_type in [dict, types.SimpleNamespace, common.MatrixEntry, defaultdict, list]:
        return _decode_ci_items(val)

    elif val_type not in type_skiplist:
        return val


def _decode_ci_items(src_obj):
    src_obj_type = type(src_obj)

    if src_obj_type == list:
        new_obj = [_parse_entry(val) for val in src_obj ]

    elif src_obj_type in [types.SimpleNamespace, common.MatrixEntry, dict, defaultdict]:
        _src_obj = vars(src_obj) \
            if src_obj_type in [types.SimpleNamespace, common.MatrixEntry] \
            else src_obj

        new_obj = {key: _parse_entry(val) for key, val in _src_obj.items()}

    else:
        new_obj = src_obj

    return new_obj


def _encode_entry(src_obj):
    src_obj_type = type(src_obj)

    if src_obj_type == list:
        return [_encode_entry(val) for val in src_obj]
    elif src_obj_type is not dict:
        return src_obj

    result = {}

    final_type = src_obj.get("$type", "dict")
    try: del src_obj['$type']
    except Exception: pass

    if final_type == "datetime":
        return datetime.datetime.fromtimestamp(src_obj.get('value'))

    for key, val in src_obj.items():
        result[key] = _encode_entry(val)

    if final_type == "defaultdict":
        return defaultdict(types.SimpleNamespace, result)

    elif final_type == "SimpleNamespace":
        return types.SimpleNamespace(**result)

    return result


def _encode_json(src_obj, name, settings):
    del src_obj['$schema']

    data = _encode_entry(src_obj)

    return common.MatrixEntry(import_key=name, processed_settings=settings, **data)


def _decode_users(results):
    output = []
    for user_idx, ods_ci in getattr(results, "ods_ci", {}).items():
        if not hasattr(ods_ci, "output"): continue

        output.append({
            'hostname': results.testpod_hostnames.get(user_idx, None),
            'steps': _decode_steps(ods_ci.output, results.notebook_pod_times.get(user_idx)),
            'succeeded': ods_ci.exit_code == 0
        })

    return output


def _decode_steps(steps, pod_times):
    out_steps = []
    for step_name, step_data in steps.items():
        out_step = {
            'name': step_name,
            'duration': (step_data.finish - step_data.start).total_seconds(),
            'status': step_data.status
        }
        if step_name in ("Wait for the Notebook Spawn", "Create and Start the Workbench"):
            out_step['substeps'] = _generate_pod_timings(pod_times, step_data.start, step_data.finish)

        out_steps.append(out_step)

    return out_steps


def _generate_pod_timings(pod_times, start, end):
    output = {}

    if hasattr(pod_times, "pod_scheduled"):
        output['resource_init_time'] = (pod_times.pod_scheduled - start).total_seconds()
    if hasattr(pod_times, "containers_ready"):
        output['container_ready_time'] = (pod_times.containers_ready - pod_times.pod_initialized).total_seconds()
    if hasattr(pod_times, 'containers_ready'):
        output['user_notification'] = (end - pod_times.containers_ready).total_seconds()

    return output
