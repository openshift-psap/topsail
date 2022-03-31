import os
import logging
import wdm

def update_env_with_env_files():
    """
    Overrides the function default args with the flags found in the environment variables files
    """
    for env in ".wdm_env", ".wdm_env.generated":
        try:
            with open(env) as f:
                for line in f.readlines():
                    key, found , value = line.strip().partition("=")
                    if not found:
                        logging.warning("invalid line in {env}: {line.strip()}")
                        continue
                    if key in os.environ: continue # prefer env to env file
                    os.environ[key] = value
        except FileNotFoundError: pass # ignore missing files


def update_kwargs_with_env(kwargs):
    # override the function default args with the flags found in the environment variables

    for flag, current_value in kwargs.items():
        if current_value: continue # already set, ignore.

        env_value = os.environ.get(f"WDM_{flag.upper()}")
        if not env_value: continue # not set, ignore.
        kwargs[flag] = env_value # override the function arg with the environment variable value


def get_config_from_kv_file(config_file):
    kv = {}
    with open(config_file) as f:
        for line in f.readlines():
            key, found , value = line.strip().partition("=")
            if not found:
                logging.warning("Invalid line in {config_file}: {line.strip()}")
                continue
            if key in kv:
                logging.warning(f"Duplicated entry in {config_file}: {key}. "
                                "Keeping only the first entry.")
                continue

            kv[key] = value

    return kv


def get_config_from_cli(cli_arg):
    config_kv = {}
    for kv in cli_arg.split(","):
        key, found, value = kv.partition("=")
        if not found:
            logging.error("Found an invalid configuration entry in the command-line: %s", kv)
            sys.exit(1)
        config_kv[key] = value
    return config_kv


def get_configuration_kv(dep):

    config_sources = [
        wdm.state.cli_configuration,
        wdm.state.dep_file_configuration,
        wdm.state.cfg_file_configuration,
    ]
    kv = {}
    for src in config_sources:
        for k, v in (src or {}).items():
            kv[k] = v

    return kv

def get_task_configuration_kv(dep, task):
    all_kv = get_configuration_kv(dep)
    if dep.config_values:
        all_kv.update(dep.config_values)

    config_requirements = (dep.spec.configuration or []) + (task and task.configuration or [])
    kv = {}
    for key in config_requirements:
        value = None

        try: value = all_kv[key]
        except KeyError:
            raise KeyError(f"Could not find a value for the configuration key '{key}'")

        kv[key] = value

    return kv
