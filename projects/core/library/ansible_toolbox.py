import itertools
import subprocess
import os
import time
import sys
import pathlib
import yaml
import tempfile
import functools
import inspect
import shutil
import shlex
import importlib
import logging

from projects.core.library import config
TOPSAIL_DIR = pathlib.Path(config.__file__).parents[3]

class Toolbox:
    """
    The Topsail Toolbox
    """

    def __init__(self):
        for toolbox_file in (TOPSAIL_DIR / "projects").glob("*/toolbox/*.py"):
            if toolbox_file.name.startswith("."): continue

            project_toolbox_module = str(toolbox_file.relative_to(TOPSAIL_DIR).with_suffix("")).replace(os.path.sep, ".")
            mod = importlib.import_module(project_toolbox_module)
            toolbox_name = toolbox_file.with_suffix("").name

            if toolbox_name.startswith("_"): continue

            if hasattr(mod, "__entrypoint"):
                self.__dict__[toolbox_name] = getattr(mod, "__entrypoint")
                continue

            try:
                self.__dict__[toolbox_name] = getattr(mod, toolbox_name.title())
            except AttributeError as e:
                logging.fatal(str(e)) # eg: AttributeError: module 'projects.notebooks.toolbox.notebooks' has no attribute 'Notebooks'
                sys.exit(1)


def AnsibleRole(role_name):
    def decorator(fct):
        fct.ansible_role = role_name

        @functools.wraps(fct)
        def call_fct(*args, **kwargs):
            run_ansible_role = fct(*args, **kwargs)

            run_ansible_role.role_name = role_name
            run_ansible_role.ansible_constants = getattr(fct, "ansible_constants", {})
            run_ansible_role.ansible_mapped_params = getattr(fct, "ansible_mapped_params", False)
            run_ansible_role.ansible_skip_config_generation = getattr(fct, "ansible_skip_config_generation", False)

            if not run_ansible_role.group:
                run_ansible_role.group = fct.__qualname__.partition(".")[0].lower()
            if not run_ansible_role.command:
                run_ansible_role.command = fct.__name__

            if not hasattr(run_ansible_role, "py_command_args"):
                run_ansible_role.py_command_args = None
            return run_ansible_role

        return call_fct

    return decorator


def AnsibleMappedParams(fct):
    fct.ansible_mapped_params = True
    return fct

def AnsibleSkipConfigGeneration(fct):
    fct.ansible_skip_config_generation = True
    return fct

def AnsibleConstant(description, name, value):
    def decorator(fct):
        if not hasattr(fct, "ansible_constants"):
            fct.ansible_constants = []
        fct.ansible_constants.append(dict(description=description, name=name, value=value))

        return fct

    return decorator

class RunAnsibleRole:
    """
    Playbook runner

    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    If you're seeing this text, put the --help flag earlier in your list
    of command-line arguments, this is a limitation of the CLI parsing library
    used by the toolbox.
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    """
    def __init__(self,
                 ansible_vars: dict = None,
                 role_name: str = None,
                 group: str = "",
                 command: str = ""):
        self.ansible_vars = ansible_vars or {}
        self.role_name = role_name
        self.group = group
        self.command = command
        self.clazz = None

    def __str__(self):
        return ""

    def _run(self):
        if not self.role_name:
            raise RuntimeError("Role not set :/")

        if self.ansible_mapped_params:
            py_params = self.ansible_vars
            self.ansible_vars = {
                f"{self.role_name}_{k}": v for k, v in py_params.items() if k != "self"
            }
            for constant in self.ansible_constants:
                self.ansible_vars[f"{self.role_name}_{constant['name']}"] = constant["value"]

        # do not modify the `os.environ` of this Python process
        env = os.environ.copy()

        remote_host = env.get("TOPSAIL_JUMP_CI_REMOTE_HOST")

        if env.get("ARTIFACT_DIR") is None:
            topsail_base_dir = pathlib.Path(env.get("TOPSAIL_BASE_DIR", "/tmp"))
            env["ARTIFACT_DIR"] = str(topsail_base_dir / f"topsail_{time.strftime('%Y%m%d')}")

        artifact_dir = pathlib.Path(env["ARTIFACT_DIR"])
        artifact_dir.mkdir(parents=True, exist_ok=True)

        prefix = env.get("ARTIFACT_TOOLBOX_NAME_PREFIX", "")
        suffix = env.get("ARTIFACT_TOOLBOX_NAME_SUFFIX", "")

        if env.get("ARTIFACT_EXTRA_LOGS_DIR") is None:
            artifact_base_dirname = f"{self.group}__{self.command}" if self.group and self.command \
                else "__".join(sys.argv[1:3])

            previous_extra_count = len(list(artifact_dir.glob("*__*")))

            name = f"{previous_extra_count:03d}__{prefix}{artifact_base_dirname}{suffix}"

            env["ARTIFACT_EXTRA_LOGS_DIR"] = str(pathlib.Path(env["ARTIFACT_DIR"]) / name)

        artifact_extra_logs_dir = pathlib.Path(env["ARTIFACT_EXTRA_LOGS_DIR"])
        artifact_extra_logs_dir.mkdir(parents=True, exist_ok=True)

        command_name = f"{self.group} {self.command}"
        if prefix:
            command_name = f"{prefix}/{command_name}"
        if suffix:
            command_name = f"{command_name}/{suffix}"

        if self.py_command_args:
            with open(artifact_extra_logs_dir / "_python.gen.cmd", "w") as f:
                print(f"{sys.argv[0]} {self.group} {self.command} \\", file=f)
                for key, _value in self.py_command_args.items():
                    value = shlex.quote(str(_value))
                    print(f"   --{key}={value} \\", file=f)
                print("   --", file=f)

            with open(artifact_extra_logs_dir / "_python.args.yaml", "w") as f:
                print(yaml.dump({self.py_command_name: self.py_command_args}), file=f)

        print(f"Using '{env['ARTIFACT_DIR']}' to store the test artifacts.")
        self.ansible_vars["artifact_dir"] = env["ARTIFACT_DIR"]

        print(f"Using '{artifact_extra_logs_dir}' to store extra log files.")
        self.ansible_vars["artifact_extra_logs_dir"] = str(artifact_extra_logs_dir)

        if env.get("ANSIBLE_LOG_PATH") is None:
            env["ANSIBLE_LOG_PATH"] = str(artifact_extra_logs_dir / "_ansible.log")
        print(f"Using '{env['ANSIBLE_LOG_PATH']}' to store ansible logs.")
        pathlib.Path(env["ANSIBLE_LOG_PATH"]).parent.mkdir(parents=True, exist_ok=True)

        if env.get("ANSIBLE_CACHE_PLUGIN_CONNECTION") is None:
            env["ANSIBLE_CACHE_PLUGIN_CONNECTION"] = str(artifact_dir / "ansible_facts")
        print(f"Using '{env['ANSIBLE_CACHE_PLUGIN_CONNECTION']}' to store ansible facts.")
        pathlib.Path(env["ANSIBLE_CACHE_PLUGIN_CONNECTION"]).parent.mkdir(parents=True, exist_ok=True)

        # We configure the roles path dynamically appending them to the defaults
        topsail_roles_list = []

        if current_roles_path := env.get("ANSIBLE_ROLES_PATH"):
            topsail_roles_list += [current_roles_path]

        topsail_roles_list += [str(entry) for entry in (TOPSAIL_DIR / "projects").glob("*/toolbox")]

        env["ANSIBLE_ROLES_PATH"] = os.pathsep.join(topsail_roles_list)
        self.ansible_vars["roles_path"] = env["ANSIBLE_ROLES_PATH"]

        # We configure the collections path dynamically
        current_collections_paths = []
        if (collect_path := env.get("ANSIBLE_COLLECTIONS_PATHS")) is not None:
            current_collections_paths.append(str(collect_path))
        for path in sys.path:
            collections_path = pathlib.Path(path) / 'ansible_collections'
            if collections_path.exists():
                current_collections_paths.append(str(collections_path))
        env["ANSIBLE_COLLECTIONS_PATHS"] = os.pathsep.join(current_collections_paths)
        self.ansible_vars["collections_paths"] = env["ANSIBLE_COLLECTIONS_PATHS"]

        if env.get("ANSIBLE_CONFIG") is None:
            env["ANSIBLE_CONFIG"] = str(TOPSAIL_DIR / "ansible-config" / "ansible.cfg")

        print(f"Using '{env['ANSIBLE_CONFIG']}' as ansible configuration file.")

        if env.get("ANSIBLE_JSON_TO_LOGFILE") is None:
            env["ANSIBLE_JSON_TO_LOGFILE"] = str(artifact_extra_logs_dir / "_ansible.log.json")
        print(f"Using '{env['ANSIBLE_JSON_TO_LOGFILE']}' as ansible json log file.")

        # the play file must be in the directory where the 'roles' are
        tmp_play_file = tempfile.NamedTemporaryFile("w+",
                                                    prefix="tmp_play_{}_".format(artifact_extra_logs_dir.name),
                                                    suffix=".yaml",
                                                    dir=os.getcwd(), delete=False)

        generated_play = [
            dict(name=f"Run {self.role_name} role",
                 roles=[self.role_name],
                 vars=self.ansible_vars,
                 )
        ]

        if remote_host:
            # gather only env values
            generated_play[0]["gather_facts"] = True
            generated_play[0]["gather_subset"] = ['env','!all','!min']

            # run remotely
            generated_play[0]["hosts"] = "remote"
            inventory_fd, path = tempfile.mkstemp()
            os.remove(path) # using only the FD. Ensures that the file disappears when this process terminates
            inventory_f = os.fdopen(inventory_fd, 'w')

            host_properties = []
            if "@" in remote_host:
                host_properties.append("ansible_user="+remote_host.split("@")[0])

            inventory_content = f"""
[all:vars]

[remote]
{remote_host.rpartition("@")[-1]} {" ".join(host_properties)}
"""

            print(inventory_content, file=inventory_f)
            inventory_f.flush()
        else:
            # run locally
            generated_play[0]["connection"] = "local"
            generated_play[0]["hosts"] = "localhost"
            generated_play[0]["gather_facts"] = False

        if extra_vars_fname := env.get("TOPSAIL_ANSIBLE_PLAYBOOK_EXTRA_VARS"):
            try:
                with open(extra_vars_fname) as f:
                    extra_vars_dict = yaml.safe_load(f)

            except yaml.parser.ParserError:
                logging.fatal(f"Could not parse file TOPSAIL_ANSIBLE_PLAYBOOK_EXTRA_VARS='{extra_vars}' as yaml ...")
                raise

            generated_play[0]["vars"] |= extra_vars_dict

        generated_play_path = artifact_extra_logs_dir / "_ansible.play.yaml"
        with open(generated_play_path, "w") as f:
            yaml.dump(generated_play, f)
        shutil.copy(generated_play_path, tmp_play_file.name)

        cmd = ["ansible-playbook", "-vv", tmp_play_file.name]

        with open(artifact_extra_logs_dir / "_ansible.env", "w") as f:
            for k, v in env.items():
                print(f"{k}={v}", file=f)

        with open(artifact_extra_logs_dir / "_python.cmd", "w") as f:
            print(" ".join(map(shlex.quote, sys.argv)), file=f)


        if remote_host:
            cmd += ["--inventory-file", f"/proc/{os.getpid()}/fd/{inventory_fd}"]

        sys.stdout.flush()
        sys.stderr.flush()

        ret = -1
        try:
            run_result = subprocess.run(cmd, env=env, check=False)
            ret = run_result.returncode
        except KeyboardInterrupt:
            print("")
            print("Interrupted :/")
            sys.exit(1)
        finally:
            try:
                os.remove(tmp_play_file.name)
            except FileNotFoundError:
                pass # play file was removed, ignore

            if ret != 0:
                extra_dir_name = pathlib.Path(env['ARTIFACT_EXTRA_LOGS_DIR']).name
                with open(artifact_extra_logs_dir / "FAILURE", "a") as f:
                    print(f"[{extra_dir_name}] {' '.join(sys.argv)} --> {ret}", file=f)

        raise SystemExit(ret)
