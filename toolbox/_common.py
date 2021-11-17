import itertools
import subprocess
import os
import time
import sys
from pathlib import Path


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
        run_ansible_playbook(self.playbook_name, self.opts)


def flatten(lst):
    return itertools.chain(*lst)


def run_ansible_playbook(playbook_name, opts: dict = dict()):
    version_override = os.environ.get("OCP_VERSION")
    if version_override is not None:
        opts["openshift_release"] = version_override

    if os.environ.get("ARTIFACT_DIR") is None:
        os.environ["ARTIFACT_DIR"] = f"/tmp/ci-artifacts_{time.strftime('%Y%m%d')}"
        print(f"Using '{os.environ['ARTIFACT_DIR']}' to store the test artifacts (default value for ARTIFACT_DIR).")
    else:
        print(f"Using '{os.environ['ARTIFACT_DIR']}' to store the test artifacts.")
    opts["artifact_dir"] = os.environ["ARTIFACT_DIR"]

    os.environ["ARTIFACT_DIRNAME"] = '__'.join(sys.argv[1:3])

    artifact_dir = Path(os.environ["ARTIFACT_DIR"])
    artifact_dir.mkdir(parents=True, exist_ok=True)

    if os.environ.get("ARTIFACT_EXTRA_LOGS_DIR") is None:
        previous_extra_count = len(list(artifact_dir.glob("*__*")))
        os.environ["ARTIFACT_EXTRA_LOGS_DIR"] = str(
            Path(os.environ["ARTIFACT_DIR"]) /
            f"{previous_extra_count:03d}__{os.environ['ARTIFACT_DIRNAME']}"
        )

    artifact_extra_logs_dir = Path(os.environ["ARTIFACT_EXTRA_LOGS_DIR"])
    artifact_extra_logs_dir.mkdir(parents=True, exist_ok=True)

    print(f"Using '{artifact_extra_logs_dir}' to store extra log files.")
    opts["artifact_extra_logs_dir"] = str(artifact_extra_logs_dir)

    if os.environ.get("ANSIBLE_LOG_PATH") is None:
        os.environ["ANSIBLE_LOG_PATH"] = str(artifact_extra_logs_dir / "_ansible.log")
    print(f"Using '{os.environ['ANSIBLE_LOG_PATH']}' to store ansible logs.")
    Path(os.environ["ANSIBLE_LOG_PATH"]).parent.mkdir(parents=True, exist_ok=True)

    if os.environ.get("ANSIBLE_CACHE_PLUGIN_CONNECTION") is None:
        os.environ["ANSIBLE_CACHE_PLUGIN_CONNECTION"] = str(artifact_dir / "ansible_facts")
    print(f"Using '{os.environ['ANSIBLE_CACHE_PLUGIN_CONNECTION']}' to store ansible facts.")
    Path(os.environ["ANSIBLE_CACHE_PLUGIN_CONNECTION"]).parent.mkdir(parents=True, exist_ok=True)

    if os.environ.get("ANSIBLE_CONFIG") is None:
        os.environ["ANSIBLE_CONFIG"] = str(top_dir / "config" / "ansible.cfg")
    print(f"Using '{os.environ['ANSIBLE_CONFIG']}' as ansible configuration file.")

    if os.environ.get("ANSIBLE_JSON_TO_LOGFILE") is None:
        os.environ["ANSIBLE_JSON_TO_LOGFILE"] = str(artifact_extra_logs_dir / "_ansible.log.json")
    print(f"Using '{os.environ['ANSIBLE_JSON_TO_LOGFILE']}' as ansible json log file.")

    if os.environ.get("JUNIT_OUTPUT_DIR") is None:
        os.environ["JUNIT_OUTPUT_DIR"] = str(artifact_extra_logs_dir / "_ansible.log.json")
    print(f"Using '{os.environ['JUNIT_OUTPUT_DIR']}' as ansible junit destination file.")

    option_flags = flatten(
        [
            ["-e", f"{option_name}={option_value}"]
            for option_name, option_value in opts.items()
        ]
    )

    cmd = ["ansible-playbook", "-vv", *option_flags, f"playbooks/{playbook_name}.yml"]

    with open(artifact_extra_logs_dir / "_ansible.cmd", "w") as f:
        print(" ".join(cmd), file=f)
    print("<+>", cmd)

    with open(artifact_extra_logs_dir / "_ansible.env", "w") as f:
        for k, v in os.environ.items():
            print(f"{k}={v}", file=f)

    os.execvpe(cmd[0], cmd, os.environ)

    raise RuntimeError("os.execvpe shouldn't return ...")
