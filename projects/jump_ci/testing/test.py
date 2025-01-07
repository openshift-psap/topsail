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

def rewrite_variables_overrides(variable_overrides_dict):
    new_variable_overrides = dict()

    old_args = variable_overrides_dict["PR_POSITIONAL_ARGS"].split()
    # remove the 2 first args of the jump-ci test (project and cluster)
    NUMBER_OF_ARGS_TO_SKIP = 2
    new_args = old_args[NUMBER_OF_ARGS_TO_SKIP:]

    new_args_str = new_variable_overrides[f"PR_POSITIONAL_ARGS"] = " ".join(new_args)
    new_variable_overrides["PR_POSITIONAL_ARGS"] = variable_overrides_dict["PR_POSITIONAL_ARG_0"]
    logging.info(f"New args to execute on the jump host: {new_args_str}")
    for idx, value in enumerate(new_args):
        new_variable_overrides[f"PR_POSITIONAL_ARG_{idx+1}"] = value

    for k, v in variable_overrides_dict.items():
        if k.startswith("PR_POSITIONAL_ARG"): continue

        NOT_FOUND = object()
        found = config.project.get_config(k, NOT_FOUND, print=False, warn=False)
        if found != NOT_FOUND:
            # the key 'k' was found in the jump-ci config.
            # It belongs to us, do *not* pass it over to the new test.
            logging.info(f"NOT passing '{k}: {v}' to the new variables overrides")

            continue

        # the key 'k' was not found in the jump-ci config
        # It doesn't belong to us, pass it to the new test
        new_variable_overrides[k] = v
        logging.info(f"Passing '{k}: {v}' to the new variables overrides")

    return new_variable_overrides


def jump_ci(command):
    @utils.entrypoint()
    def do_jump_ci(cluster=None, project=None, test_args=""):
        """
        Runs a command in the Jump Host.

        Args:
          cluster: the name of the cluster to run on
          project: the name of the project to launch
          test_args: the test args to pass to the test command
        """

        # Open the tunnel
        tunnelling.prepare()

        if cluster is None:
            cluster = config.project.get_config("cluster.name")

        run.run_toolbox("jump_ci", "ensure_lock", cluster=cluster)

        secrets_path_env_key = config.project.get_config("secrets.dir.env_key")

        env_fd_path, env_file = utils.get_tmp_fd()
        extra_env = dict(
            TOPSAIL_JUMP_CI="true",
            TOPSAIL_JUMP_CI_INSIDE_JUMP_HOST="true",
        )

        env_pass_lists = config.project.get_config("env.pass_lists", print=False)

        env_pass_list = set()
        for _, pass_list in (env_pass_lists or {}).items():
            env_pass_list.update(pass_list)

        for k, v in (os.environ | extra_env).items():
            if k not in env_pass_list: continue

            print(f"{k}={shlex.quote(v)}", file=env_file)

        env_file.flush()

        variable_overrides_file = pathlib.Path(os.environ.get("ARTIFACT_DIR")) / "variable_overrides.yaml"

        if not test_args and not variable_overrides_file.exists():
            logging.fatal(f"File '{variable_overrides_file}' does not exist, and --test_args not passed. Please specify one of them :/")
            raise SystemExit(1)

        if test_args and not project:
            logging.fatal(f"The --project flag must be specificed when --test_args is passed")
            raise SystemExit(1)

        if test_args:
            variables_overrides_dict = dict(
                PR_POSITIONAL_ARGS=test_args,
                PR_POSITIONAL_ARG_0="jump-ci",
            )

            for idx, arg in enumerate(test_args.split()):
                variables_overrides_dict[f"PR_POSITIONAL_ARG_{idx+1}"] = arg

            config.project.set_config("overrides", variable_overrides_dict)

        else:
            if not os.environ.get("OPENSHIFT_CI") == "true":
                logging.fatal("Not running in OpenShift CI. Don't know how to rewrite the variable_overrides_file. Aborting.")
                raise SystemExit(1)

            project = config.project.get_config("overrides.PR_POSITIONAL_ARG_2")

            variables_overrides_dict = rewrite_variables_overrides(
                config.project.get_config("overrides")
            )

        run.run_toolbox(
            "jump_ci", "prepare_step",
            cluster=cluster,
            project=project,
            step=command,
            env_file=env_fd_path,
            variables_overrides_dict=variables_overrides_dict,
            secrets_path_env_key=secrets_path_env_key,
        )

        try:
            tunnelling.run_with_ansible_ssh_conf(f"bash /tmp/{cluster}/test/{command}/entrypoint.sh")
            logging.info(f"Test step '{command}' on cluster '{cluster}' succeeded.")
            failed = False
        except subprocess.CalledProcessError as e:
            logging.fatal(f"Test step '{command}' on cluster '{cluster}' FAILED.")
            failed = True

        run.run_toolbox(
            "jump_ci", "retrieve_artifacts",
            cluster=cluster,
            remote_dir=f"test/{command}/artifacts",
            local_dir=f"../test-artifacts", # copy to the main artifact directory
            mute_stdout=True,
        )

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
