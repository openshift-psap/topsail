import itertools
import subprocess
import os
import time
import sys
from pathlib import Path
import yaml
import tempfile
import functools
import inspect
import shutil
import shlex

top_dir = Path(__file__).resolve().parent.parent

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

        version_override = os.environ.get("OCP_VERSION")

        if version_override is not None:
            self.ansible_vars["openshift_release"] = version_override

        if self.ansible_mapped_params:
            py_params = self.ansible_vars
            self.ansible_vars = {
                f"{self.role_name}_{k}": v for k, v in py_params.items() if k != "self"
            }
            for constant in self.ansible_constants:
                self.ansible_vars[f"{self.role_name}_{constant['name']}"] = constant["value"]

        # do not modify the `os.environ` of this Python process
        env = os.environ.copy()

        if env.get("ARTIFACT_DIR") is None:
            ci_artifact_base_dir = Path(env.get("CI_ARTIFACT_BASE_DIR", "/tmp"))
            env["ARTIFACT_DIR"] = str(ci_artifact_base_dir / f"ci-artifacts_{time.strftime('%Y%m%d')}")

        artifact_dir = Path(env["ARTIFACT_DIR"])
        artifact_dir.mkdir(parents=True, exist_ok=True)

        prefix = env.get("ARTIFACT_TOOLBOX_NAME_PREFIX", "")
        suffix = env.get("ARTIFACT_TOOLBOX_NAME_SUFFIX", "")

        if env.get("ARTIFACT_EXTRA_LOGS_DIR") is None:
            artifact_base_dirname = f"{self.group}__{self.command}" if self.group and self.command \
                else "__".join(sys.argv[1:3])

            previous_extra_count = len(list(artifact_dir.glob("*__*")))

            name = f"{previous_extra_count:03d}__{prefix}{artifact_base_dirname}{suffix}"

            env["ARTIFACT_EXTRA_LOGS_DIR"] = str(Path(env["ARTIFACT_DIR"]) / name)

        artifact_extra_logs_dir = Path(env["ARTIFACT_EXTRA_LOGS_DIR"])
        artifact_extra_logs_dir.mkdir(parents=True, exist_ok=True)

        command_name = f"{self.group} {self.command}"
        if prefix:
            command_name = f"{prefix}/{command_name}"
        if suffix:
            command_name = f"{command_name}/{suffix}"

        if self.py_command_args:
            with open(artifact_extra_logs_dir / "_python.gen.cmd", "w") as f:
                print(f"{sys.argv[0]} {self.group} {self.command} \\", file=f)
                for key, value in self.py_command_args.items():
                    print(f"   --{key}='{value}' \\", file=f)
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
        Path(env["ANSIBLE_LOG_PATH"]).parent.mkdir(parents=True, exist_ok=True)

        if env.get("ANSIBLE_CACHE_PLUGIN_CONNECTION") is None:
            env["ANSIBLE_CACHE_PLUGIN_CONNECTION"] = str(artifact_dir / "ansible_facts")
        print(f"Using '{env['ANSIBLE_CACHE_PLUGIN_CONNECTION']}' to store ansible facts.")
        Path(env["ANSIBLE_CACHE_PLUGIN_CONNECTION"]).parent.mkdir(parents=True, exist_ok=True)

        if env.get("ANSIBLE_CONFIG") is None:
            env["ANSIBLE_CONFIG"] = str(top_dir / "config" / "ansible.cfg")
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
                 connection="local",
                 gather_facts=False,
                 hosts="localhost",
                 roles=[self.role_name],
                 vars=self.ansible_vars,
                 )
        ]

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
                extra_dir_name = Path(env['ARTIFACT_EXTRA_LOGS_DIR']).name
                with open(artifact_extra_logs_dir / "FAILURE", "w") as f:
                    print(f"[{extra_dir_name}] {' '.join(sys.argv)} --> {ret}", file=f)

        raise SystemExit(ret)
