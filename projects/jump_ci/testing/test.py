#!/usr/bin/env python

import sys, os, shlex
import subprocess
import fire
import pathlib
import logging
logging.getLogger().setLevel(logging.INFO)
import yaml

from projects.core.library import env, config, run, configure_logging
configure_logging()

from projects.jump_ci.testing import utils, prepare_jump_ci, tunnelling

def jump_ci(command):
    @utils.entrypoint()
    def do_jump_ci(test_args=""):
        """
        Runs a command in the Jump Host.

        Args:
          test_args: the test args to pass to the test command
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

        if not test_args and not variable_overrides_file.exists():
            logging.fatal(f"File '{variable_overrides_file}' does not exist, and --test_args not passed. Please specify one of them :/")
            raise SystemExit(1)

        if test_args:
            variable_overrides_dict = dict(
                PR_POSITIONAL_ARGS=test_args,
                PR_POSITIONAL_ARG_0="jump-ci",
            )

            for idx, arg in enumerate(test_args.split()):
                variable_overrides_dict[f"PR_POSITIONAL_ARG_{idx+1}"] = arg

            with open(variable_overrides_file, "w") as f:
                print(yaml.dump(variable_overrides_dict), file=f)

        extra_variables_overrides = {
            "_rhoai_.skip_args": 1,
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

        try:
            tunnelling.run_with_ansible_ssh_conf(f"bash /tmp/{cluster}/test/{command}/entrypoint.sh")
            logging.info(f"Test step '{command}' on cluster '{cluster}' succeeded.")
            failed = False
        except subprocess.CalledProcessError as e:
            logging.fatal(f"Test step '{command}' on cluster '{cluster}' FAILED.")
            failed = True

        if failed:
            raise SystemExit(1)

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
