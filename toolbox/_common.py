import itertools
import subprocess
import os
import time
import sys
from pathlib import Path
import yaml
import tempfile

top_dir = Path(__file__).resolve().parent.parent


class PlaybookRun:
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
    def __init__(self, playbook_name, opts: dict = None):
        if opts is None:
            opts = {}

        self.playbook_name = playbook_name
        self.opts = opts

    def __str__(self):
        return ""

    def _run(self):
        run_ansible_role(self.playbook_name, self.opts)


def flatten(lst):
    return itertools.chain(*lst)


def run_ansible_role(role_name, opts: dict = dict()):
    version_override = os.environ.get("OCP_VERSION")
    if version_override is not None:
        opts["openshift_release"] = version_override

    # do not modify the `os.environ` of this Python process
    env = os.environ.copy()

    if env.get("ARTIFACT_DIR") is None:
        env["ARTIFACT_DIR"] = f"/tmp/ci-artifacts_{time.strftime('%Y%m%d')}"
        print(f"Using '{env['ARTIFACT_DIR']}' to store the test artifacts (default value for ARTIFACT_DIR).")
    else:
        print(f"Using '{env['ARTIFACT_DIR']}' to store the test artifacts.")
    opts["artifact_dir"] = env["ARTIFACT_DIR"]

    env["ARTIFACT_DIRNAME"] = '__'.join(sys.argv[1:3])

    artifact_dir = Path(env["ARTIFACT_DIR"])
    artifact_dir.mkdir(parents=True, exist_ok=True)

    if env.get("ARTIFACT_EXTRA_LOGS_DIR") is None:
        previous_extra_count = len(list(artifact_dir.glob("*__*")))
        env["ARTIFACT_EXTRA_LOGS_DIR"] = str(
            Path(env["ARTIFACT_DIR"]) /
            f"{previous_extra_count:03d}__{env['ARTIFACT_DIRNAME']}"
        )

    artifact_extra_logs_dir = Path(env["ARTIFACT_EXTRA_LOGS_DIR"])
    artifact_extra_logs_dir.mkdir(parents=True, exist_ok=True)

    print(f"Using '{artifact_extra_logs_dir}' to store extra log files.")
    opts["artifact_extra_logs_dir"] = str(artifact_extra_logs_dir)

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

    option_flags = flatten(
        [
            ["-e", f"{option_name}={option_value}"]
            for option_name, option_value in opts.items()
        ]
    )

    tmp_play_file = tempfile.NamedTemporaryFile("w+", dir=os.getcwd(), delete=False)
    play = [
        dict(name=f"Run {role_name} role",
             connection="local",
             gather_facts=False,
             hosts="localhost",
             roles=[role_name],
             )
    ]
    yaml.dump(play, tmp_play_file)
    tmp_play_file.close()

    cmd = ["ansible-playbook", "-vv", *option_flags, tmp_play_file.name]

    with open(artifact_extra_logs_dir / "_ansible.cmd", "w") as f:
        print(" ".join(cmd), file=f)
    print("<+>", cmd)

    with open(artifact_extra_logs_dir / "_ansible.env", "w") as f:
        for k, v in env.items():
            print(f"{k}={v}", file=f)
    try:
        run_result = subprocess.run(cmd, env=env, check=False)
        ret = run_result.returncode
    finally:
        os.remove(tmp_play_file.name)

    raise SystemExit(ret)
