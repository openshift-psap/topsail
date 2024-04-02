import datetime
import logging
import yaml, json

import config, run

def create_resource(resource_json_template, resource_name_template,
                      index, verbose_resource_creation, dry_run):
    K8S_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
    schedule_time = datetime.datetime.now().strftime(K8S_TIME_FMT)
    resource_json = resource_json_template
    resource_json = resource_json.replace("{SCHEDULE-TIME}", schedule_time)
    resource_json = resource_json.replace("{INDEX}", f"{index:03d}")

    resource_name = resource_name_template.replace("{INDEX}", f"{index:03d}")

    if verbose_resource_creation:
        logging.info(f"Creating resource #{index} {resource_name} ...")

    if index == 0:
        logging.info(f"First resource: {resource_json}")

    if not dry_run:
        process = run.run_in_background("oc create -f-".split(" "), input=resource_json, verbose=verbose_resource_creation, capture_stdout=not verbose_resource_creation)
    else:
        process = None

    return resource_name, process

# https://stackoverflow.com/questions/1094841/get-human-readable-version-of-file-size
def sizeof_fmt(num, suffix=""):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"

def get_json_resource(resources):
    dst_file = config.ARTIFACT_DIR / f"resource_template.yaml"
    logging.info(f"Saving resource template into {dst_file}")

    dst_file.unlink(missing_ok=True)

    for res in resources:
        with open(dst_file, "a") as f:
            yaml.dump(res, f)
            print("---", file=f)

    json_resource = "\n".join([json.dumps(res) for res in resources])

    return json_resource
