import types
import datetime
import json
from pathlib import PosixPath
from collections import defaultdict, OrderedDict
import logging

import matrix_benchmarking.store as store
import matrix_benchmarking.store.simple as store_simple
import matrix_benchmarking.common as common
import matrix_benchmarking.cli_args as cli_args


def _parse_lts_dir(add_to_matrix, dirname, import_settings):
    with open(f'{dirname}/data.json') as f:
        data = json.load(f)
        add_to_matrix(_encode_json(data, dirname, data['settings']))


def _parse_entry(val):
    type_skiplist = [PosixPath, types.FunctionType]

    val_type = type(val)
    if val_type is datetime.datetime:
        return {"$type": val_type.__name__, "value": datetime.datetime.timestamp(val)}
    elif val_type in [dict, types.SimpleNamespace, common.MatrixEntry, defaultdict, list]:
        parsed = _decode_ci_items(val)
        if val_type not in [list, dict]:
            parsed["$type"] = val_type.__name__
        return parsed
    elif val_type not in type_skiplist:
        return val


def _decode_ci_items(obj):
    obj_type = type(obj)

    if obj_type == list:
        return [ _parse_entry(val) for val in obj ]
    elif obj_type in [types.SimpleNamespace, common.MatrixEntry, dict, defaultdict]:
        if obj_type in [types.SimpleNamespace, common.MatrixEntry]:
            obj = vars(obj)
        res = {}
        for (key, val) in obj.items():
            res[key] = _parse_entry(val)
        return res
    return obj


def _encode_entry(obj):
    obj_type = type(obj)

    if obj_type == list:
        return [ _encode_entry(val) for val in obj ]
    elif obj_type is not dict:
        return obj

    result = {}    
    final_type = obj.get("$type", "dict")
    try:
        del obj['$type']
    except Exception:
        pass
    
    if final_type == "datetime":
        return datetime.datetime.fromtimestamp(obj.get('value'))

    for (key, val) in obj.items():
        result[key] = _encode_entry(val)

    if final_type == "defaultdict":
        return defaultdict(types.SimpleNamespace, result)
    elif final_type == "SimpleNamespace":
        return types.SimpleNamespace(**result)
    return result 
         

def _encode_json(obj, name, settings):
    del obj['$schema']
    data = _encode_entry(obj)
    return common.MatrixEntry(import_key=name, processed_settings=settings, **data)


def _decode_steps(data: dict) -> dict:
    try:
        results: dict = data['results']['ods_ci']
    except KeyError:
        return data
    
    for (key, _) in results.items():
        if key != "$type":
            end_dict = {}
            for (step, val) in results[key]['output'].items():
                step = " ".join(step.split(' ')[1:])
                end_dict[f"{step}"] = val
            results[key]['output'] = end_dict
    return data


def _convert_steps(data: dict) -> dict:
    try:
        results: dict = data['results']['ods_ci']
    except KeyError:
        return data

    for (key, _) in results.items():
        counter = 0
        if key != "$type":
            end_dict = {}
            if 'output' in results[key].keys():
                for (step, val) in results[key]['output'].items():
                    end_dict[f"{counter}. {step}"] = val
                    counter += 1
                results[key]['output'] = end_dict
    return data


def build_lts_payloads() -> dict:
    entry: common.MatrixEntry = None
    for (_, entry) in common.Matrix.processed_map.items():
        start_time = entry.results.start_time
        end_time = entry.results.end_time
        data = _decode_ci_items(entry)

        yield {
            "$schema": "urn:rhods-matbench-upload:2.0.0",
            **_convert_steps(data)
        }, start_time, end_time


def build_limited_lts_payload() -> dict:
    for(_, entry) in common.Matrix.processed_map.items():
        RESULTS = entry.results
        output = {
            "$schema": "urn:rhods-matbench-upload:3.0.0",
            "users": _decode_limited_users(RESULTS.ods_ci, RESULTS.testpod_hostnames),
            'rhods_version': RESULTS.rhods_info.version,
            'ocp_version': RESULTS.sutest_ocp_version
        }
        
        yield output, 0, 0


def _decode_limited_users(users, hostnames):
    output = []
    for (key, val) in users.items():
        output.append({
            'hostname': hostnames[key],
            'steps': _decode_limited_steps(val.output)
        })

    return output


def _decode_limited_steps(steps):
    out_steps = []
    for (step_name, step_data) in steps.items():
        out_steps.append({
            'name': step_name,
            'duration': (step_data.finish - step_data.start).total_seconds(),
            'success': step_data.status
        })
    return out_steps
