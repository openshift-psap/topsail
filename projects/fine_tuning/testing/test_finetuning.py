import sys, os
import logging
import traceback
import copy
import pathlib
import yaml
import uuid
import time

from projects.core.library import env, config, run, visualize, matbenchmark
import prepare_finetuning

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
TOPSAIL_DIR = pathlib.Path(config.__file__).parents[3]
RUN_DIR = pathlib.Path(os.getcwd()) # for run_one_matbench
os.chdir(TOPSAIL_DIR)


def reset_prometheus(delay=60):
    if not config.ci_artifacts.get_config("tests.capture_prom"):
        logging.info("tests.capture_prom is disabled, skipping Prometheus DB reset")
        return

    with run.Parallel("cluster__reset_prometheus_dbs") as parallel:
        parallel.delayed(run.run_toolbox, "cluster", "reset_prometheus_db", mute_stdout=True)
        if config.ci_artifacts.get_config("tests.capture_prom_uwm"):
            parallel.delayed(run.run_toolbox_from_config, "cluster", "reset_prometheus_db", suffix="uwm", artifact_dir_suffix="_uwm", mute_stdout=True)

    logging.info(f"Wait {delay}s for Prometheus to restart collecting data ...")
    time.sleep(delay)


def dump_prometheus(delay=60):
    if not config.ci_artifacts.get_config("tests.capture_prom"):
        logging.info("tests.capture_prom is disabled, skipping Prometheus DB dump")
        return

    logging.info(f"Wait {delay}s for Prometheus to finish collecting data ...")
    time.sleep(delay)

    with run.Parallel("cluster__dump_prometheus_dbs") as parallel:
        parallel.delayed(run.run_toolbox, "cluster", "dump_prometheus_db", mute_stdout=True)
        if config.ci_artifacts.get_config("tests.capture_prom_uwm"):
            parallel.delayed(run.run_toolbox_from_config, "cluster", "dump_prometheus_db", suffix="uwm", artifact_dir_suffix="_uwm", mute_stdout=True)



def prepare_matbench_test_files():

    with open(env.ARTIFACT_DIR / "settings.yaml", "w") as f:
        settings = dict(
            fine_tuning=True,
        )

        yaml.dump(settings, f, indent=4)

        with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
            yaml.dump(config.ci_artifacts.config, f, indent=4)

        with open(env.ARTIFACT_DIR / ".uuid", "w") as f:
            print(str(uuid.uuid4()), file=f)


def test():
    prepare_finetuning.prepare_namespace()

    with env.NextArtifactDir("test_fine_tuning"):
        prepare_matbench_test_files
        reset_prometheus()
        exit_code = 1
        try:
            run.run_toolbox_from_config("fine_tuning", "run_fine_tuning_job")
            exit_code = 0
        finally:
            with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                print(f"{exit_code}", file=f)

            dump_prometheus()
