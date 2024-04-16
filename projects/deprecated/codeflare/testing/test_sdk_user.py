import logging
import yaml
import os, sys
import pathlib
import importlib

import prepare_sdk_user, prepare_user_pods

from projects.core.library import env, config, run, visualize

def _run_many(test_artifact_dir_p):
    # argument 'test_artifact_dir_p' is a pointer to
    # 'test_artifact_dir', like by-reference arguments of C the reason
    # for this C-ism is that this way, test_artifact_dir can be
    # returned to the caller even if the test fails and raises an
    # exception (so that we can run the visualization even if the test
    # failed)
    dry_mode = config.ci_artifacts.get_config("tests.dry_mode")

    def prepare_matbench_files():
        with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
            yaml.dump(config.ci_artifacts.config, f, indent=4)

        user_count = config.ci_artifacts.get_config("tests.sdk_user.user_count")
        with open(env.ARTIFACT_DIR / "settings.yaml", "w") as f:
            settings = dict(user_count=user_count)
            yaml.dump(settings, f, default_flow_style=False, sort_keys=False)

    next_count = env.next_artifact_index()
    test_artifact_dir_p[0] = \
        test_artifact_dir = env.ARTIFACT_DIR / f"{next_count:03d}__sdk_user_run_many"

    with env.TempArtifactDir(test_artifact_dir):

        prepare_matbench_files()

        failed = True
        try:
            if dry_mode:
                logging.info("local_ci run_multi --suffix sdk_user ==> skipped")
            else:
                run.run_toolbox_from_config("local_ci", "run_multi", suffix="sdk_user")

            failed = False
        finally:
            with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                print("1" if failed else "0", file=f)

            if not dry_mode:
                #run.run_toolbox("cluster", "capture_environment", mute_stdout=True, check=False)
                pass


def test(dry_mode=None, visualize=None, capture_prom=None):
    """
    Runs the test from the CI

    Args:
      dry_mode: if True, do not execute the tests, only list what would be executed
      visualize: if False, do not generate the visualization reports
      capture_prom: if False, do not capture Prometheus database
    """

    prepare_user_pods.apply_prefer_pr()

    if visualize is not None:
        config.ci_artifacts.set_config("tests.visualize", visualize)
    if capture_prom is not None:
        config.ci_artifacts.set_config("tests.capture_prom", capture_prom)
    if dry_mode is not None:
        config.ci_artifacts.set_config("tests.dry_mode", dry_mode)

    try:
        test_artifact_dir_p = [None]
        try:
            _run_many(test_artifact_dir_p)
        finally:
            if not visualize:
                logging.info(f"Visualization disabled.")
            elif test_artifact_dir_p[0] is not None:
                next_count = env.next_artifact_index()
                with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__plots"):
                    visualize.prepare_matbench()
                    visualize.generate_from_dir(test_artifact_dir_p[0])
            else:
                logging.warning("Not generating the visualization as the test artifact directory hasn't been created.")

    finally:
        if config.ci_artifacts.get_config("clusters.cleanup_on_exit"):
            prepare_sdk_user.cleanup_cluster()


def run_one():
    """
    Runs one codeflare SDK user test
    """

    logging.info("Runs one codeflare SDK user test")
    job_index = os.environ.get("JOB_COMPLETION_INDEX")
    if job_index is not None:
        namespace = config.ci_artifacts.get_config("tests.sdk_user.namespace")
        new_namespace = f"{namespace}-user-{job_index}"
        logging.info(f"Running in a parallel job. Changing the pipeline test namespace to '{new_namespace}'")
        config.ci_artifacts.set_config("tests.sdk_user.namespace", new_namespace)
    else:
        job_index = 0

    namespace = config.ci_artifacts.get_config("tests.sdk_user.namespace")
    prepare_sdk_user.prepare_user_namespace()

    if user_index := config.ci_artifacts.get_config("tests.sdk_user.user_index") is not None:
        msg = f"The user index 'tests.sdk_user.user_index' should have been null at this point. Value: {user_index}"
        logging.error(msg)
        raise ValueError(msg)

    config.ci_artifacts.set_config("tests.sdk_user.user_index", job_index)

    user_directory = config.ci_artifacts.get_config("tests.sdk_user.user_code.directory")
    user_entrypoint = config.ci_artifacts.get_config("tests.sdk_user.user_code.entrypoint")


    def timeout(func, args=(), kwargs={}, timeout_duration=1, default=None):
        # https://stackoverflow.com/questions/492519/timeout-on-a-function-call
        import signal

        class TimeoutError(Exception):
            pass

        def handler(signum, frame):
            raise TimeoutError(f"Function {func.__module__}.{func.__name__} from {func.__code__.co_filename} timed out after {timeout_duration} seconds ...")

        # set the timeout handler
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(timeout_duration)
        try:
            return func(*args, **kwargs)
        finally:
            signal.alarm(0)

    orig_wd = pathlib.Path(os.getcwd())

    next_count = env.next_artifact_index()
    with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__run_one"):
        src_dir = orig_wd / "projects/codeflare/testing/sdk_user" / user_directory

        run.run(f"cp -rv {src_dir}/* {env.ARTIFACT_DIR}")

        sys.path.append(str(env.ARTIFACT_DIR))
        os.chdir(env.ARTIFACT_DIR)
        try:
            entrypoint = importlib.__import__(user_entrypoint)

            timeout(entrypoint.main,
                    timeout_duration=20*60, # 20 minutes
                    )
        finally:
            sys.path.pop()
            os.chdir(orig_wd)

        run.run_toolbox("codeflare", "capture_state", namespace=namespace)

        run.run_toolbox("codeflare", "cleanup_appwrappers", namespace=namespace)
        run.run(f"oc delete rayclusters --all -n {namespace}")

    logging.info("All done.")
