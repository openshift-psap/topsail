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

        with open(env.ARTIFACT_DIR / "settings", "w") as f:
            print("scale_test=true", f)

        with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
            yaml.dump(config.ci_artifacts.config, f, indent=4)

        failed = True
        try:
            if capture_prom:
                run.run("./run_toolbox.py cluster reset_prometheus_db",
                        capture_stdout=True)

            run_test()

            if capture_prom:
                run.run("./run_toolbox.py cluster dump_prometheus_db",
                        capture_stdout=True)
            failed = False
        finally:
            with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                print("1" if failed else "0", file=f)

            if not dry_mode:
                run.run("./run_toolbox.py from_config cluster capture_environment --suffix sample",
                        capture_stdout=True)

def run_test():
    run.run("testing/watsonx-serving/poc/deploy-model.sh | tee $ARTIFACT_DIR/000_deploy-model_sh.log")
    run.run("testing/watsonx-serving/poc/try_kserve.sh | tee $ARTIFACT_DIR/001_try_kserve_sh.log")

    run.run("mkdir -p $ARTIFACT_DIR/artifacts")
    run.run("oc get all -n kserve-demo > $ARTIFACT_DIR/artifacts/all.status")
    run.run("oc get pods -owide -n kserve-demo > $ARTIFACT_DIR/artifacts/pods.status")

    for what in "all", "pods", "deployments", "serving", "inferenceservice", "servingruntime":
        run.run(f"oc get {what} -oyaml -n kserve-demo > $ARTIFACT_DIR/artifacts/{what}.yaml", check=False)
