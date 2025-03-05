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

    idx = 0
    for idx, value in enumerate(new_args):
        new_variable_overrides[f"PR_POSITIONAL_ARG_{idx+1}"] = value
    next_pr_positional_arg_count = idx + 2

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

    return new_variable_overrides, next_pr_positional_arg_count


def jump_ci(command):
    @utils.entrypoint()
    def do_jump_ci(cluster=None, project=None, test_args=None):
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

        secrets_path_env_key = config.project.get_config("secrets.dir.env_key")

        extra_env = dict(
            TOPSAIL_JUMP_CI="true",
            TOPSAIL_JUMP_CI_INSIDE_JUMP_HOST="true",
        )

        def prepare_env_file(_extra_env):
            env_fd_path, env_file = utils.get_tmp_fd()

            env_pass_lists = config.project.get_config("env.pass_lists", print=False)

            env_pass_list = set()
            for _, pass_list in (env_pass_lists or {}).items():
                env_pass_list.update(pass_list)

            for k, v in (os.environ | _extra_env).items():
                if k not in (env_pass_list | _extra_env.keys()): continue

                print(f"{k}={shlex.quote(v)}", file=env_file)

            env_file.flush()

            return env_fd_path, env_file

        variable_overrides_file = pathlib.Path(os.environ.get("ARTIFACT_DIR")) / "variable_overrides.yaml"

        if test_args is None and not variable_overrides_file.exists():
            logging.fatal(f"File '{variable_overrides_file}' does not exist, and --test_args not passed. Please specify one of them :/")
            raise SystemExit(1)

        if test_args is not None and not project:
            logging.fatal(f"The --project flag must be specificed when --test_args is passed")
            raise SystemExit(1)

        run.run_toolbox("jump_ci", "ensure_lock", cluster=cluster, owner=utils.get_lock_owner())

        cluster_lock_dir = f" /tmp/topsail_{cluster}"

        if test_args is not None:
            variables_overrides_dict = dict(
                PR_POSITIONAL_ARGS=test_args,
                PR_POSITIONAL_ARG_0="jump-ci",
            )

            for idx, arg in enumerate(test_args.split()):
                variables_overrides_dict[f"PR_POSITIONAL_ARG_{idx+1}"] = arg

            config.project.set_config("overrides", variables_overrides_dict)
            next_pr_positional_arg_count = idx + 2
        else:
            if not os.environ.get("OPENSHIFT_CI") == "true":
                logging.fatal("Not running in OpenShift CI. Don't know how to rewrite the variable_overrides_file. Aborting.")
                raise SystemExit(1)

            project = config.project.get_config("overrides.PR_POSITIONAL_ARG_2")

            variables_overrides_dict, next_pr_positional_arg_count = rewrite_variables_overrides(
                config.project.get_config("overrides")
            )

        for idx, multi_run_args in enumerate((config.project.get_config("multi_run.args") or [...])):
            multi_run_args_dict = {}
            multi_run_dirname = None
            test_artifacts_dirname = "test-artifacts"

            if multi_run_args is not ...:

                multi_run_args_lst = multi_run_args if isinstance(multi_run_args, list) else [multi_run_args]
                multi_run_dirname = f"multi_run__{'_'.join(multi_run_args_lst)}"

                with open(env.ARTIFACT_DIR / "multi_run_args.list", "a+") as f:
                    print(f"{multi_run_dirname}: {multi_run_args}")

                for idx, multi_run_arg in enumerate(multi_run_args_lst):
                    variables_overrides_dict[f"PR_POSITIONAL_ARG_{next_pr_positional_arg_count+idx}"] = multi_run_arg

            with env.NextArtifactDir(multi_run_dirname) if multi_run_dirname else open("/dev/null"):

                if multi_run_dirname:
                    test_artifacts_dirname = f"{env.ARTIFACT_DIR.name}/{test_artifacts_dirname}"

                if step_dir := os.environ.get("TOPSAIL_OPENSHIFT_CI_STEP_DIR"):
                    # see "jump_ci retrieve_artifacts" below
                    extra_env["TOPSAIL_OPENSHIFT_CI_STEP_DIR"] = f"{step_dir}/{test_artifacts_dirname}"

                env_fd_path, env_file = prepare_env_file(extra_env)

                run.run_toolbox(
                    "jump_ci", "prepare_step",
                    cluster=cluster,
                    lock_owner=utils.get_lock_owner(),
                    project=project,
                    step=command,
                    env_file=env_fd_path,
                    variables_overrides_dict=(variables_overrides_dict | multi_run_args_dict),
                    secrets_path_env_key=secrets_path_env_key,
                )
                env_file.close()

                try:
                    tunnelling.run_with_ansible_ssh_conf(f"bash {cluster_lock_dir}/test/{command}/entrypoint.sh")
                    logging.info(f"Test step '{command}' on cluster '{cluster}' succeeded.")
                    failed = False
                except subprocess.CalledProcessError as e:
                    logging.fatal(f"Test step '{command}' on cluster '{cluster}' FAILED.")
                    failed = True
                except run.SignalError as e:
                    logging.error(f"Caught signal {e.sig}. Aborting.")
                    raise
                finally:
                    # always run the cleanup to be sure that the container doesn't stay running
                    tunnelling.run_with_ansible_ssh_conf(f"bash {cluster_lock_dir}/test/{command}/entrypoint.sh cleanup")

                run.run_toolbox(
                    "jump_ci", "retrieve_artifacts",
                    cluster=cluster,
                    lock_owner=utils.get_lock_owner(),
                    remote_dir=f"test/{command}/artifacts",
                    local_dir=f"../{pathlib.Path(test_artifacts_dirname).name}", # copy to the main artifact directory
                    mute_stdout=True,
                    mute_stderr=True,
                )

            if failed and config.project.get_config("multi_run.stop_on_error"):
                break

        jump_ci_artifacts = env.ARTIFACT_DIR / "jump-ci-artifacts"
        jump_ci_artifacts.mkdir(parents=True, exist_ok=True)
        run.run(f'mv {env.ARTIFACT_DIR}/*__jump_ci_* {jump_ci_artifacts}/')

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
