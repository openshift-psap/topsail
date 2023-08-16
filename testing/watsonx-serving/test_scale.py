import logging
import pathlib
import yaml
import time

from common import env, config, run


def test(test_artifact_dir_p=None):
    dry_mode = config.ci_artifacts.get_config("tests.dry_mode")
    capture_prom = config.ci_artifacts.get_config("tests.capture_prom")

    if dry_mode:
        capture_prom = False

    next_count = env.next_artifact_index()
    with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__scale_test"):
        if test_artifact_dir_p is not None:
            test_artifact_dir_p[0] = env.ARTIFACT_DIR

        with open(env.ARTIFACT_DIR / "settings.yaml", "w") as f:
            yaml.dump(dict(scale_test=True), f, indent=4)


        with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
            yaml.dump(config.ci_artifacts.config, f, indent=4)

        failed = True
        try:
            if capture_prom:
                run.run("./run_toolbox.py cluster reset_prometheus_db")

            logging.info("Waiting 5 minutes to capture some metrics in Prometheus ...")

            if not dry_mode:
                time.sleep(5 * 60)

            if capture_prom:
                run.run("./run_toolbox.py cluster dump_prometheus_db")
            failed = False
        finally:
            with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                print("1" if failed else "0", file=f)

            if not dry_mode:
                run.run("./run_toolbox.py from_config cluster capture_environment --suffix sample")
