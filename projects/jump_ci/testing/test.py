#!/usr/bin/env python

import sys, os, shlex
import subprocess
import fire
import pathlib
import logging
logging.getLogger().setLevel(logging.INFO)


from projects.core.library import env, config, run, configure_logging
configure_logging()

from projects.jump_ci.testing import utils, prepare_jump_ci, tunnelling

def jump_ci(command):
    @utils.entrypoint()
    def do_jump_ci():
        """
        *Jump-CI* Runs the command in the Jump Host.
        """

        # Open the tunnel
        tunnelling.prepare()

        cluster = config.project.get_config("cluster.name")

        #run.run_toolbox("jump_ci", "ensure_lock", cluster=cluster)

        secrets_path_env_key = config.project.get_config("secrets.dir.env_key")

        env_fd_path, env_file = utils.get_tmp_fd()
        for k, v in os.environ.items():
            print(f"export {k}={shlex.quote(v)}", file=env_file)

        variable_overrides_file = pathlib.Path(os.environ.get("ARTIFACT_DIR")) / "variable_overrides.yaml"
        if not variable_overrides_file.exists():
            raise FileNotFoundError(f"File '{variable_overrides_file}' does not exist :/")

        extra_variables_overrides = {
            "_rhoai_.skip_args": 2,
        }

        run.run_toolbox(
            "jump_ci", "prepare_step",
            cluster=cluster,
            step=command,
            env_file=env_fd_path,
            variables_overrides_file=variable_overrides_file,
            extra_variables_overrides=extra_variables_overrides,
            secrets_path_env_key=secrets_path_env_key,
        )

        #tunnelling.run_with_ansible_ssh_conf(f"bash /tmp/{cluster}/test_artifacts/{step}")

    return do_jump_ci


class JumpCi:
    """
    Commands for launching the Jump CI
    """

    def __init__(self):
        self.pre_cleanup_ci = jump_ci("pre_cleanup_ci")
        self.post_cleanup_ci = jump_ci("post_cleanup_ci")
        self.prepare_ci = jump_ci("prepare_ci")
        self.test_ci = jump_ci("test_ci")

        self.generate_plots_from_pr_args = jump_ci("generate_plots_from_pr_args")


def main():
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    fire.Fire(JumpCi())


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{e.cmd}' failed --> {e.returncode}")
        sys.exit(1)
