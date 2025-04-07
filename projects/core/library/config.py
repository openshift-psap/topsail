import logging
logging.getLogger().setLevel(logging.INFO)
import os, sys
import pathlib
import yaml
import shutil
import subprocess
import threading
import re
from collections import defaultdict
import jsonpath_ng
import copy

from . import env
from . import run
from . import common

TOPSAIL_DIR = pathlib.Path(common.__file__).parents[3]
VARIABLE_OVERRIDES_FILENAME = "variable_overrides.yaml"
PR_ARG_KEY = "PR_POSITIONAL_ARG_"

project = None # the project config will be populated in init()

class TempValue(object):
    def __init__(self, config, key, value):
        self.config = config
        self.key = key
        self.value = value
        self.prev_value = None

    def __enter__(self):
        self.prev_value = self.config.get_config(self.key, print=False)
        self.config.set_config(self.key, self.value)

        return True

    def __exit__(self, ex_type, ex_value, exc_traceback):
        self.config.set_config(self.key, self.prev_value)

        return False # If we returned True here, any exception would be suppressed!


class Config:
    def __init__(self, testing_dir, config_path):
        self.testing_dir = testing_dir
        self.config_path = config_path

        if not self.config_path.exists():
            msg = f"Configuration file '{self.config_path}' does not exist :/"
            logging.error(msg)
            raise ValueError(msg)

        logging.info(f"Loading configuration from {self.config_path} ...")
        with open(self.config_path) as config_f:
            self.config = yaml.safe_load(config_f)


    def apply_config_overrides(self, *, ignore_not_found=False, variable_overrides_path=None, log=True):
        if variable_overrides_path is None:
            variable_overrides_path = env.ARTIFACT_DIR / VARIABLE_OVERRIDES_FILENAME

        if not variable_overrides_path.exists():
            logging.debug(f"apply_config_overrides: {variable_overrides_path} does not exist, nothing to override.")

            return

        with open(variable_overrides_path) as f:
            variable_overrides = yaml.safe_load(f)

        if not isinstance(variable_overrides, dict):
            msg = f"Wrong type for the variable overrides file. Expected a dictionnary, got {variable_overrides.__class__.__name__}"
            logging.fatal(msg)
            raise ValueError(msg)

        for key, value in variable_overrides.items():
            MAGIC_DEFAULT_VALUE = object()
            handled_secretly = True # current_value MUST NOT be printed below.
            current_value = self.get_config(key, MAGIC_DEFAULT_VALUE, print=False, warn=False, handled_secretly=handled_secretly)
            if current_value == MAGIC_DEFAULT_VALUE:
                if ignore_not_found:
                    continue

                if "." in key:
                    raise ValueError(f"Config key '{key}' does not exist, and cannot create it at the moment :/")

                self.config[key] = None

            self.set_config(key, value, print=False)
            actual_value = self.get_config(key, print=False) # ensure that key has been set, raises an exception otherwise
            if log:
                logging.info(f"config override: {key} --> {actual_value}")


    def apply_preset(self, name):
        try:
            values = self.get_config(f'ci_presets["{name}"]', print=False)
        except IndexError:
            logging.error(f"Preset '{name}' does not exists :/")
            raise

        logging.info(f"Applying preset '{name}' ==> {values}")
        if values is None:
            raise ValueError(f"Preset '{name}' does not exists")

        presets = self.get_config("ci_presets.names", print=False) or []
        if not name in presets:
            self.set_config("ci_presets.names", presets + [name])

        for key, value in values.items():
            if key == "extends":
                for extend_name in value:
                    self.apply_preset(extend_name)
                continue

            msg = f"preset[{name}] {key} --> {value}"
            logging.info(msg)
            with open(env.ARTIFACT_DIR / "presets_applied", "a") as f:
                print(msg, file=f)

            self.set_config(key, value, print=False)

    def get_config(self, jsonpath, default_value=..., warn=True, print=True, handled_secretly=False):
        try:
            value = jsonpath_ng.parse(jsonpath).find(self.config)[0].value
        except IndexError as ex:
            if default_value != ...:
                if warn:
                    logging.warning(f"get_config: {jsonpath} --> missing. Returning the default value: {default_value}")
                return default_value

            logging.error(f"get_config: {jsonpath} --> {ex}")
            raise KeyError(f"Key '{jsonpath}' not found in {self.config_path}")

        if isinstance(value, str) and value.startswith("*$@"):
            print = False

        value = self.resolve_reference(value, handled_secretly)

        if print and not handled_secretly:
            logging.info(f"get_config: {jsonpath} --> {value}")

        return value


    def set_config(self, jsonpath, value, print=True):
        if threading.current_thread().name != "MainThread":
            msg = f"set_config({jsonpath}, {value}) cannot be called from a thread, to avoid race conditions."
            if os.environ.get("OPENSHIFT_CI") or os.environ.get("PERFLAB_CI"):
                logging.error(msg)
                with open(env.ARTIFACT_DIR / "SET_CONFIG_CALLED_FROM_THREAD", "a") as f:
                    print(msg, file=f)
            else:
                raise RuntimeError(msg)

        try:
            self.get_config(jsonpath, print=False, handled_secretly=True) # will raise an exception if the jsonpath does not exist
            jsonpath_ng.parse(jsonpath).update(self.config, value)
        except Exception as ex:
            logging.error(f"set_config: {jsonpath}={value} --> {ex}")
            raise

        if print:
            logging.info(f"set_config: {jsonpath} --> {value}")

        with open(self.config_path, "w") as f:
            yaml.dump(self.config, f, indent=4, default_flow_style=False, sort_keys=False)

        if (shared_dir := os.environ.get("SHARED_DIR")) and (shared_dir_path := pathlib.Path(shared_dir)) and shared_dir_path.exists():

            with open(shared_dir_path / "config.yaml", "w") as f:
                yaml.dump(self.config, f, indent=4)

    def save_config_overrides(self):
        variable_overrides_path = env.ARTIFACT_DIR / VARIABLE_OVERRIDES_FILENAME

        if not variable_overrides_path.exists():
            logging.debug(f"save_config_overrides: {variable_overrides_path} does not exist, nothing to save.")
            self.config["overrides"] = {}
            return

        with open(variable_overrides_path) as f:
            variable_overrides = yaml.safe_load(f)

        self.config["overrides"] = variable_overrides

    def apply_preset_from_pr_args(self):
        for config_key in self.get_config("$", print=False).keys():
            if not config_key.startswith(PR_ARG_KEY): continue
            if config_key == f"{PR_ARG_KEY}0": continue

            presets = self.get_config(config_key)
            if not presets: continue
            for preset in presets.strip().split(" "):
                self.apply_preset(preset)

    def detect_apply_light_profile(self, profile, name_suffix="light"):
        if os.environ.get("OPENSHIFT_CI"):
            job_name_safe = os.environ.get("JOB_NAME_SAFE", ...)

            if job_name_safe is ...:
                raise RuntimeError("Running in OpenShift CI but JOB_NAME_SAFE not set :/")

            if job_name_safe != name_suffix and not job_name_safe.endswith(f"-{name_suffix}"):
                return False

            logging.info(f"Running a '{name_suffix}' test ({job_name_safe}), applying the '{profile}' profile")

            self.apply_preset(profile)

            if os.environ.get("HOSTNAME") == "light-prepare":
                common.prepare_light_cluster()

            return True

        logging.info("Not running in OpenShift CI, no light environment to detect.")

        return False

    def detect_apply_metal_profile(self, profile):
        platform_type_cmd = run.run("oc get infrastructure/cluster -ojsonpath={.status.platformStatus.type}", capture_stdout=True, capture_stderr=True, check=False)
        if platform_type_cmd.returncode != 0:
            logging.warning(f"Failed to get the platform type: {platform_type_cmd.stderr.strip()}")
            logging.warning("Ignoring the metal profile check.")
            return False

        platform_type = platform_type_cmd.stdout
        logging.info(f"detect_apply_metal_profile: infrastructure/cluster.status.platformStatus.type = {platform_type}")
        if platform_type not in ("BareMetal", "None", "IBMCloud"):
            logging.info("detect_apply_metal_profile: Assuming not running in a bare-metal environment.")
            return False
        logging.info(f"detect_apply_metal_profile: Assuming running in a bare-metal environment. Applying the '{profile}' profile.")

        self.apply_preset(profile)
        return True

    def detect_apply_cluster_profile(self, node_profiles):
        cluster_nodes_cmd = run.run("oc get nodes -oname", capture_stdout=True, capture_stderr=True, check=False)
        if cluster_nodes_cmd.returncode != 0:
            logging.warning(f"Failed to get the cluster nodes: {cluster_nodes_cmd.stderr.strip()}")
            logging.warning("Ignoring the cluster profile check.")
            return False

        for node_name in cluster_nodes_cmd.stdout.split():
            for node, profile in node_profiles.items():
                if f"node/{node}" != node_name:
                    continue

                self.apply_preset(profile)
                return profile

        return False

    def resolve_reference(self, value, handled_secretly=False):
        if not isinstance(value, str): return value
        if "@" not in value: return value

        # --- #

        def secret_file_dereference():
            if not handled_secretly:
                msg = f"{value} is a secret dereference, but get_config(..., handled_secretly=False). Aborting"
                logging.fatal(msg)
                raise ValueError(msg)

            ref_key = value.removeprefix("*$@")
            ref_value = self.get_config(ref_key, print=False)

            secret_dir = pathlib.Path(os.environ[self.get_config("secrets.dir.env_key", print=False)])
            secret_value = (secret_dir / ref_value).read_text().strip()

            return secret_value


        # --- #

        def simple_dereference():
            ref_key = value[1:]
            return self.get_config(ref_key)


        def multi_dereference():
            new_value = value
            for ref in re.findall(r"\{@.*?\}", value):
                ref_key = ref.strip("{@}")
                ref_value = self.get_config(ref_key, print=False)
                new_value = new_value.replace(ref, str(ref_value))

            return new_value

        # --- #

        if value.startswith("*$@"):
            return secret_file_dereference()

        if value.startswith("*@"):
            msg = f"resolve_reference: '*@' references not supported (not sure how to handle it wrt to secrets) --> {k}: {value}"
            logging.fatal(msg)
            raise ValueError(msg)

        if not (value.startswith("@") or "{@" in value):
            # don't go further if the derefence anchor isn't found
            return value

        # --- #


        new_value = simple_dereference() if value.startswith("@") \
            else multi_dereference()

        if not handled_secretly:
            logging.info(f"resolve_reference: {value} ==> '{new_value}'")

        return copy.deepcopy(new_value)


def _set_config_environ(testing_dir):
    reloading = False
    config_path_final = pathlib.Path(env.ARTIFACT_DIR / "config.yaml")

    config_file_src = None
    if (env_config_file_src := os.environ.get("TOPSAIL_FROM_CONFIG_FILE")):
        config_file_src = env_config_file_src
        logging.info(f"Loading the configuration from TOPSAIL_FROM_CONFIG_FILE={config_file_src} ...")

    elif ((shared_dir_file_src := pathlib.Path(os.environ.get("SHARED_DIR", "/not-a-directory")) / "config.yaml")
          and shared_dir_file_src.exists()):
        config_file_src = shared_dir_file_src
        logging.info(f"Reloading the config file from SHARED_DIR {config_file_src} ...")
    else:
        config_file_src = testing_dir / "config.yaml"
        logging.info(f"Reloading the config file from TOPSAIL project directory {config_file_src} ...")

    os.environ["TOPSAIL_FROM_CONFIG_FILE"] = str(config_path_final)

    if "TOPSAIL_FROM_COMMAND_ARGS_FILE" not in os.environ:
        os.environ["TOPSAIL_FROM_COMMAND_ARGS_FILE"] = str(testing_dir / "command_args.yml.j2")

    if not pathlib.Path(config_file_src) == config_path_final:

        logging.info(f"Copying the configuration from {config_file_src} to the artifact dir ...")
        shutil.copyfile(config_file_src, config_path_final)

    return config_path_final


def get_command_arg(group, command, arg, prefix=None, suffix=None, mute=False):
    try:
        if not mute:
            logging.info(f"get_command_arg: {group} {command} {arg}")

        proc = run.run_toolbox_from_config(group, command, show_args=arg,
                                           prefix=prefix, suffix=suffix,
                                           check=True,
                                           run_kwargs=dict(capture_stdout=True, capture_stderr=True, log_command=(not mute)))
    except subprocess.CalledProcessError as e:
        logging.error(e.stderr.strip().decode("ascii", "ignore"))
        raise

    return proc.stdout.strip()


def set_jsonpath(config, jsonpath, value):
    get_jsonpath(config, jsonpath) # will raise an exception if the jsonpath does not exist
    jsonpath_ng.parse(jsonpath).update(config, value)

def get_jsonpath(config, jsonpath):
    return jsonpath_ng.parse(jsonpath).find(config)[0].value


def test_skip_list():
    if len(sys.argv) < 2:
        logging.info(f"test_skip_list: cannot determinate the current subcommand. Not processing the skip list.")
        return

    current_subcommand = sys.argv[1]
    logging.info(f"Currently running the subcommand '{current_subcommand}'")

    exec_list = project.get_config("exec_list", None, print=False)
    if exec_list is None:
        logging.warning("The exec_list isn't defined in this project.")
        exec_list = {}

    NOT_FOUND = object()
    exec_this_subcommand = exec_list.get(current_subcommand, NOT_FOUND)
    if exec_this_subcommand is NOT_FOUND:
        logging.info(f"Subcommand '{current_subcommand}' is not defined in the exec list. Executing this command by default.")
        return

    if exec_this_subcommand is False:
        logging.fatal(f"Subcommand '{current_subcommand}' is disabled in the exec list. Stopping happily this execution.")
        with open(env.ARTIFACT_DIR / "SKIPPED", "w") as f:
            print("Skipped because part of the \skip list", file=f)
        raise SystemExit(0)

    if exec_this_subcommand is not True and exec_list.get("_only_", False):
        logging.fatal(f"Only flag is set, and subcommand '{current_subcommand}' is not enabled in the exec list. Stopping happily this execution.")
        with open(env.ARTIFACT_DIR / "SKIPPED", "w") as f:
            print("Skipped because not part of the \only list", file=f)

        raise SystemExit(0)

    # not in the skip list
    # not the only command to execute
    # continue happilly =:-)

    pass


def init(testing_dir, apply_preset_from_pr_args=False, apply_config_overrides=True):
    global project

    if project:
        logging.info("config.init: project config already configured.")
        return

    config_path = _set_config_environ(testing_dir)
    project = Config(testing_dir, config_path)

    if os.environ.get("TOPSAIL_LOCAL_CI_MULTI") == "true":
        logging.info("config.init: running in a local-ci multi Pod, skipping apply_config_overrides and apply_preset_from_pr_args.")
        return

    if not apply_config_overrides:
        logging.info("config.init: running with 'apply_config_overrides', skipping the overrides. Saving it as 'overrides' field in the project configuration.")
        project.save_config_overrides()
        return

    repo_var_overrides = TOPSAIL_DIR / VARIABLE_OVERRIDES_FILENAME

    if repo_var_overrides.exists():
        logging.info(f"Found '{repo_var_overrides}', apply the variables overrides from it.")
        project.apply_config_overrides(variable_overrides_path=repo_var_overrides)

    ci_presets_to_apply = project.get_config("ci_presets.to_apply", [], warn=False)
    if isinstance(ci_presets_to_apply, str):
        ci_presets_to_apply = [ci_presets_to_apply]

    for preset in ci_presets_to_apply:
        project.apply_preset(preset)

    variable_overrides_to_apply = project.get_config("ci_presets.variable_overrides", {}, warn=False)
    for var_name, var_value in variable_overrides_to_apply.items():
        project.set_config(var_name, var_value)

    if repo_var_overrides.exists():
        # reapply to force overrides on top of presets
        project.apply_config_overrides(variable_overrides_path=repo_var_overrides, log=False)

    project.apply_config_overrides()

    if apply_preset_from_pr_args:
        project.apply_preset_from_pr_args()
        # reapply to force overrides on top of presets
        project.apply_config_overrides(log=False)

    test_skip_list()

    pass
