import logging
import pathlib
import yaml, json
import time
import os
import datetime
import uuid

from topsail.testing import env, config, run
import prepare_scale

def test(test_artifact_dir_p=None):
    dry_mode = config.ci_artifacts.get_config("tests.dry_mode")
    capture_prom = config.ci_artifacts.get_config("tests.capture_prom")

    if dry_mode:
        capture_prom = False

    with env.NextArtifactDir("scale_test"):
        if test_artifact_dir_p is not None:
            test_artifact_dir_p[0] = env.ARTIFACT_DIR

        with open(env.ARTIFACT_DIR / "settings.yaml", "w") as f:
            yaml.dump(dict(scale_test=True), f, indent=4)

        with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
            yaml.dump(config.ci_artifacts.config, f, indent=4)

        with open(env.ARTIFACT_DIR / ".uuid", "w") as f:
            print(str(uuid.uuid4()), file=f)

        failed = True
        try:
            run_test(dry_mode)

            failed = False
        finally:
            with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                print("1" if failed else "0", file=f)

            if not dry_mode:
                try:
                    run.run_toolbox("kserve", "capture_operators_state", mute_stdout=True)
                finally:
                    run.run_toolbox("cluster", "capture_environment", mute_stdout=True)


def run_test(dry_mode):
    if dry_mode:
        logging.info("local_ci run_multi --suffix sdk_user ==> skipped")
    else:
        run.run_toolbox_from_config("local_ci", "run_multi", suffix="scale")


def prepare_user_sutest_namespace(namespace):
    if run.run(f'oc get project "{namespace}" -oname 2>/dev/null', check=False).returncode == 0:
        logging.warning(f"Project {namespace} already exists.")
        (env.ARTIFACT_DIR / "PROJECT_ALREADY_EXISTS").touch()
        return

    run.run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')
    label = config.ci_artifacts.get_config("tests.scale.namespace.label")
    run.run(f"oc label ns/{namespace} {label} --overwrite")

    metal = config.ci_artifacts.get_config("clusters.sutest.is_metal")
    dedicated = config.ci_artifacts.get_config("clusters.sutest.compute.dedicated")
    if not metal and dedicated:
        extra = dict(project=namespace)
        run.run_toolbox_from_config("cluster", "set_project_annotation", prefix="sutest", suffix="scale_test_node_selector", extra=extra, mute_stdout=True)
        run.run_toolbox_from_config("cluster", "set_project_annotation", prefix="sutest", suffix="scale_test_toleration", extra=extra, mute_stdout=True)

    with env.NextArtifactDir("deploy_storage_configuration"):
        deploy_storage_configuration(namespace)

    if not config.ci_artifacts.get_config("kserve.raw_deployment.enabled"):
        deploy_istio_sidecar(namespace)


def save_and_create(name, content, namespace, is_secret=False):
    (env.ARTIFACT_DIR / "src").mkdir(exist_ok=True)
    file_path = pathlib.Path("/tmp") / name if is_secret \
        else env.ARTIFACT_DIR / "src" / name

    try:
        with open(file_path, "w") as f:
            print(content, file=f)

        with open(file_path) as f:
            run.run(f"oc apply -f- -n {namespace}", stdin_file=f)
    finally:
        if is_secret:
            file_path.unlink(missing_ok=True)


def prepare_namespace(namespace):
    deploy_storage_configuration(namespace)
    deploy_istio_sidecar()


def deploy_istio_sidecar(namespace):
    istio_sidecar = f"""\
apiVersion: networking.istio.io/v1beta1
kind: Sidecar
metadata:
  name: default
  namespace: {namespace}
spec:
  egress:
  - hosts:
    - "./*"
    - "istio-system/*"
"""
    save_and_create("istio_sidecar.yaml", istio_sidecar, namespace)


def deploy_storage_configuration(namespace):
    storage_secret_name = config.ci_artifacts.get_config("kserve.storage_config.name")
    region = config.ci_artifacts.get_config("kserve.storage_config.region")
    endpoint = config.ci_artifacts.get_config("kserve.storage_config.endpoint")
    use_https = config.ci_artifacts.get_config("kserve.storage_config.use_https")

    access_key = None
    secret_key = None

    vault_key = config.ci_artifacts.get_config("secrets.dir.env_key")
    aws_cred_filename = config.ci_artifacts.get_config("secrets.aws_cred")
    aws_cred_file = pathlib.Path(os.environ[vault_key]) / aws_cred_filename
    logging.info(f"Reading AWS credentials from '{aws_cred_filename}' ...")
    with open(aws_cred_file) as f:
        for line in f.readlines():
            if line.startswith("aws_access_key_id "):
                access_key = line.rpartition("=")[-1].strip()
            if line.startswith("aws_secret_access_key "):
                secret_key = line.rpartition("=")[-1].strip()

    if None in (access_key, secret_key):
        raise ValueError(f"aws_access_key_id or aws_secret_access_key not found in {aws_cred_file} ...")

    storage_secret = f"""\
apiVersion: v1
kind: Secret
metadata:
  annotations:
    serving.kserve.io/s3-region: "{region}"
    serving.kserve.io/s3-endpoint: "{endpoint}"
    serving.kserve.io/s3-usehttps: "{use_https}"
  name: {storage_secret_name}
stringData:
  AWS_ACCESS_KEY_ID: "{access_key}"
  AWS_SECRET_ACCESS_KEY: "{secret_key}"
"""
    save_and_create("storage_secret.yaml", storage_secret, namespace, is_secret=True)

    # oc describe secret is safe
    run.run(f"oc describe secret/{storage_secret_name} -n {namespace} > {env.ARTIFACT_DIR / 'src' / 'storage-config.desc'}")

    # Service Account

    service_account_name = config.ci_artifacts.get_config("kserve.sa_name")
    service_account = f"""\
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {service_account_name}
secrets:
- name: {storage_secret_name}
"""

    save_and_create("ServiceAccount.yaml", service_account, namespace)


def run_one():
    logging.info("Runs one KServe user scale test")

    job_index = os.environ.get("JOB_COMPLETION_INDEX")
    if job_index is not None:
        namespace = config.ci_artifacts.get_config("tests.scale.namespace.name")
        new_namespace = f"{namespace}-u{job_index}"
        logging.info(f"Running in a parallel job. Changing the test namespace to '{new_namespace}'")
        config.ci_artifacts.set_config("tests.scale.namespace.name", new_namespace)
    else:
        job_index = 0

    namespace = config.ci_artifacts.get_config("tests.scale.namespace.name")
    sync_file = pathlib.Path("/tmp/test_done")
    sync_file.unlink(missing_ok=True)

    try:
        prepare_scale.consolidate_model_config("tests.scale.model")
        config.ci_artifacts.set_config("tests.scale.model.consolidated", True)

        prepare_user_sutest_namespace(namespace)

        def watch_failures(namespaces):
            logging.info(f"watch_internal: launching the watch loop")
            WATCH_INTERNAL = 5 # seconds
            while not sync_file.exists():
                pod_status = run.run(f"oc get pods -n {namespace} --no-headers", capture_stdout=True, log_command=False).stdout
                if "Terminating" in pod_status:
                    msg = f"Pod being terminated detected in namespace {namespace}. Aborting the test."
                    logging.error(msg)
                    logging.info("Pod status:\n{pod_status}")
                    raise RuntimeError(msg)

                NL = "\n"
                logging.info(f"watch_failures: no Pod being terminated out of {len(pod_status.split(NL)) - 1}")
                time.sleep(WATCH_INTERNAL)
            logging.info(f"watch_internal: {sync_file} has been created, exiting the watch loop")

        def test_and_mark_as_done(*args, **kwargs):
            try: run_one_test(*args, **kwargs)
            finally: sync_file.touch()

        with run.Parallel("test_and_watch_failures", dedicated_dir=False) as parallel:
            parallel.delayed(test_and_mark_as_done, namespace, job_index)
            parallel.delayed(watch_failures, namespace)

    finally:
        run.run_toolbox("kserve", "capture_state", namespace=namespace, mute_stdout=True)
        sync_file.unlink(missing_ok=True)


def run_one_test(namespace, job_index):
    models_per_namespace = config.ci_artifacts.get_config("tests.scale.model.replicas")
    inference_service_basename = config.ci_artifacts.get_config("tests.scale.model.name")
    all_inference_service_names = []
    for model_idx in range(models_per_namespace):
        inference_service_name = f"u{job_index}-m{model_idx}"

        extra = dict(
            inference_service_name=inference_service_name,
            inference_service_model_format=config.ci_artifacts.get_config("tests.scale.model.format"),
            raw_deployment=config.ci_artifacts.get_config("kserve.raw_deployment.enabled"),
        )

        run.run_toolbox_from_config("kserve", "deploy_model", extra=extra, artifact_dir_suffix=f"_{inference_service_name}")
        run.run(f'echo "model_{model_idx}_deployed: $(date)" >> "{env.ARTIFACT_DIR}/progress_ts.yaml"')

        validate_extra = dict(
            inference_service_names=[inference_service_name],
            method=config.ci_artifacts.get_config("kserve.inference_service.validation.method"),
            raw_deployment=config.ci_artifacts.get_config("kserve.raw_deployment.enabled"),
        )

        if validate_extra["raw_deployment"]:
            validate_extra["proto"] = config.ci_artifacts.get_config("kserve.inference_service.validation.proto")

        run.run_toolbox_from_config("kserve", "validate_model", extra=extra, artifact_dir_suffix=f"_{inference_service_name}")
        run.run(f'echo "model_{model_idx}_validated: $(date)" >> "{env.ARTIFACT_DIR}/progress_ts.yaml"')

        all_inference_service_names += [inference_service_name]

    extra = dict(inference_service_names=all_inference_service_names)

    run.run_toolbox_from_config("kserve", "validate_model", extra=extra, artifact_dir_suffix=f"_all")
    run.run(f'echo "model_all_validated: $(date)" >> "{env.ARTIFACT_DIR}/progress_ts.yaml"')
