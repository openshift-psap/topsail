import logging
import pathlib
import yaml, json
import time
import os
import datetime

from common import env, config, run


def test(test_artifact_dir_p=None):
    dry_mode = config.ci_artifacts.get_config("tests.dry_mode")
    capture_prom = config.ci_artifacts.get_config("tests.capture_prom")

    if dry_mode:
        capture_prom = False

    if capture_prom:
        run.run("./run_toolbox.py cluster reset_prometheus_db",
                capture_stdout=True)

    next_count = env.next_artifact_index()
    with env.TempArtifactDir(env.ARTIFACT_DIR / f"{next_count:03d}__scale_test"):
        if test_artifact_dir_p is not None:
            test_artifact_dir_p[0] = env.ARTIFACT_DIR

        with open(env.ARTIFACT_DIR / "settings", "w") as f:
            print("scale_test=true", file=f)

        with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
            yaml.dump(config.ci_artifacts.config, f, indent=4)

        failed = True
        try:
            try:
                run_test(dry_mode)
            finally:
                if capture_prom:
                    run.run("./run_toolbox.py cluster dump_prometheus_db",
                            capture_stdout=True)

            failed = False
        finally:
            with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
                print("1" if failed else "0", file=f)

            if not dry_mode:
                try:
                    run.run("./run_toolbox.py watsonx_serving capture_operators_state",
                            capture_stdout=True)
                finally:
                    run.run("./run_toolbox.py cluster capture_environment",
                            capture_stdout=True)

def run_test(dry_mode):
    if dry_mode:
        logging.info("local_ci run_multi --suffix sdk_user ==> skipped")
    else:
        run.run(f"./run_toolbox.py from_config local_ci run_multi --suffix scale")


def prepare_user_namespace(namespace):
    if run.run(f'oc get project "{namespace}" -oname 2>/dev/null', check=False).returncode == 0:
        logging.warning(f"Project {namespace} already exists.")
        (env.ARTIFACT_DIR / "PROJECT_ALREADY_EXISTS").touch()
        return

    run.run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')

    if run.run("""oc patch smmr/default -n istio-system --type=json -p="[{'op': 'add', 'path': '/spec/members/-', 'value': \""""+namespace+"""\"}]" """, check=False).returncode != 0:
        smmr_members = run.run("oc get smmr/default -n istio-system  -ojsonpath={.spec.members} | jq .[] -r", capture_stdout=True).stdout
        if namespace not in smmr_members.split("\n"):
            msg = f"Could not patch the SMMR :/. Current members: {smmr_members}"
            logging.error(msg)
            raise RuntimeError(msg)

        logging.warning(f"Namespace '{namespace}' was already in the SMMR members. Continuing.")


    run.run(f"oc get smmr/default -n istio-system -oyaml > {env.ARTIFACT_DIR / 'istio-system_smmr-default.yaml'}")

    dedicated = config.ci_artifacts.get_config("clusters.sutest.compute.dedicated")
    if dedicated:
        run.run("./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix scale_test_node_selector")
        run.run("./run_toolbox.py from_config cluster set_project_annotation --prefix sutest --suffix scale_test_toleration")


def save_and_create(name, content, namespace):
    with open(env.ARTIFACT_DIR / "src" / name, "w") as f:
        print(content, file=f)

    with open(env.ARTIFACT_DIR / "src" / name) as f:
        run.run(f"oc apply -f- -n {namespace}", stdin_file=f)


def deploy_serving_runtime(namespace):
    # Storage Secret

    # warning: do not use save_and_create() as this handles a secret
    storage_secret = run.run(f"""oc get secret/storage-config -n minio -ojson \
            | jq 'del(.metadata.namespace) | del(.metadata.uid) | del(.metadata.creationTimestamp) | del(.metadata.resourceVersion)' \
            | oc apply -f- -n {namespace}""")

    run.run(f"oc describe secret/storage-config -n {namespace} > {env.ARTIFACT_DIR / 'src' / 'storage-config.desc'}") # oc describe secret is safe

    # Service Account

    service_account = """\
apiVersion: v1
kind: ServiceAccount
metadata:
  name: sa
secrets:
- name: storage-config
"""

    save_and_create("ServiceAccount.yaml", service_account, namespace)

    # Serving Runtime

    serving_runtime_image = config.ci_artifacts.get_config("watsonx_serving.serving_runtime.image")
    serving_runtime_resource_request = json.dumps(config.ci_artifacts.get_config("watsonx_serving.serving_runtime.resource_request"))

    serving_runtime = f"""\
apiVersion: serving.kserve.io/v1alpha1
kind: ServingRuntime
metadata:
  name: caikit-runtime
spec:
  containers:
  - env:
    - name: RUNTIME_LOCAL_MODELS_DIR
      value: /mnt/models
    image: {serving_runtime_image}
    name: kserve-container
    ports:
    # Note, KServe only allows a single port, this is the gRPC port. Subject to change in the future
    - containerPort: 8085
      name: h2c
      protocol: TCP
    resources:
      requests: {serving_runtime_resource_request}
  multiModel: false
  supportedModelFormats:
  # Note: this currently *only* supports caikit format models
  - autoSelect: true
    name: caikit
"""

    save_and_create("ServingRuntime.yaml", serving_runtime, namespace)


def deploy_inference_service(namespace):
    # Inference Service
    name = "caikit-example-isvc"
    storageUri = "s3://modelmesh-example-models/llm/models"

    inference_service = f"""\
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  annotations:
    serving.knative.openshift.io/enablePassthrough: "true"
    sidecar.istio.io/inject: "true"
    sidecar.istio.io/rewriteAppHTTPProbers: "true"
  name: {name}
spec:
  predictor:
    serviceAccountName: sa
    model:
      modelFormat:
        name: caikit
      runtime: caikit-runtime
      storageUri: {storageUri}
"""

    save_and_create("InferenceService.yaml", inference_service, namespace)

    tries = 0
    retries_left = 60 * 3 # 15 min
    target_model_state = "<not queried>"
    start_time = datetime.datetime.now()
    while True:
        tries += 1

        target_model_state = run.run(f"oc get inferenceservice/caikit-example-isvc -ojsonpath={{.status.modelStatus.states.targetModelState}} -n {namespace}", capture_stdout=True).stdout

        if target_model_state == "Loaded":
            logging.info("The InferenceService is ready :)")
            break

        retries_left -= 1
        if retries_left == 0:
            break

        logging.info(f"Waiting for the model state to be 'Loaded'. Current state: {target_model_state}")
        logging.info(f"{retries_left} retries left")
        time.sleep(5)

    end_time = datetime.datetime.now()


    inferenceservice_ready = dict(start_time=start_time, end_time=end_time,
                                  tries=tries,
                                  duration_s=(end_time - start_time).total_seconds(),
                                  final_target_model_state=target_model_state)

    if retries_left == 0:
        raise RuntimeError(f"The InferenceService never got ready :/ Current state: {target_model_state}")



    logging.info(f"The InferenceService turned to the 'Loaded' state after {inferenceservice_ready['duration_s']:.0f} seconds.")

    with open(env.ARTIFACT_DIR / 'progress' / "inferenceservice_ready.yaml", "w") as f:
        yaml.dump(inferenceservice_ready, f, indent=4)

def validate_model_deployment(namespace):
    ksvc_hostname = run.run(f"oc get ksvc caikit-example-isvc-predictor -n {namespace} -o jsonpath='{{.status.url}}' | sed 's|https://||'", capture_stdout=True).stdout.strip()
    logging.info(f"KSVC hostname: {ksvc_hostname}")

    logging.info(f"Querying the TextGenerationTaskPredict endpoint ...")

    tries = 0
    retries_left = 600
    start_time = datetime.datetime.now()
    while True:
        tries += 1
        retcode = run.run(f"""grpcurl -insecure -d '{{"text": "At what temperature does liquid Nitrogen boil?"}}' -H "mm-model-id: flan-t5-small-caikit" {ksvc_hostname}:443 caikit.runtime.Nlp.NlpService/TextGenerationTaskPredict > {env.ARTIFACT_DIR}/artifacts/TextGenerationTaskPredict.answer""", check=False).returncode

        if retcode == 0:
            break

        if tries == 1:
            run.run(f"""grpcurl -insecure -d '{{"text": "At what temperature does liquid Nitrogen boil?"}}' -H "mm-model-id: flan-t5-small-caikit" {ksvc_hostname}:443 caikit.runtime.Nlp.NlpService/TextGenerationTaskPredict &> {env.ARTIFACT_DIR}/artifacts/Invalid.answer""", check=False)

        time.sleep(0.5)

        retries_left -= 1
        if retries_left == 0:
            raise RuntimeError(f"The model in {namespace} did not respond properly... Started at {start_time.time()}, stopped at {datetime.datetime.now().time()}. Tried {tries} times.")

    end_time = datetime.datetime.now()
    model_ready = dict(start_time=start_time, end_time=end_time,
                       tries=tries,
                       duration_s=(end_time - start_time).total_seconds())

    with open(env.ARTIFACT_DIR / 'progress' / "model_ready.yaml", "w") as f:
        yaml.dump(model_ready, f, indent=4)

    logging.info(f"The model responded properly after {model_ready['duration_s']:.0f} seconds.")

    logging.info(f"Querying the ServerStreamingTextGenerationTaskPredict endpoint ...")
    run.run(f"""grpcurl -insecure -d '{{"text": "At what temperature does liquid Nitrogen boil?"}}' -H "mm-model-id: flan-t5-small-caikit" {ksvc_hostname}:443 caikit.runtime.Nlp.NlpService/ServerStreamingTextGenerationTaskPredict > {env.ARTIFACT_DIR}/artifacts/ServerStreamingTextGenerationTaskPredict.answer""")

    logging.info("All done :)")


def run_one():

    logging.info("Runs one WatsonX user scale test")
    job_index = os.environ.get("JOB_COMPLETION_INDEX")
    if job_index is not None:
        namespace = config.ci_artifacts.get_config("tests.scale.namespace")
        new_namespace = f"{namespace}-user-{job_index}"
        logging.info(f"Running in a parallel job. Changing the pipeline test namespace to '{new_namespace}'")
        config.ci_artifacts.set_config("tests.scale.namespace", new_namespace)
    else:
        job_index = 0

    (env.ARTIFACT_DIR / "src").mkdir(exist_ok=True)
    (env.ARTIFACT_DIR / "progress").mkdir(exist_ok=True)
    (env.ARTIFACT_DIR / "artifacts").mkdir(exist_ok=True)

    namespace = config.ci_artifacts.get_config("tests.scale.namespace")
    try:
        prepare_user_namespace(namespace)

        deploy_serving_runtime(namespace)
        deploy_inference_service(namespace)
        validate_model_deployment(namespace)
    finally:
        run.run(f"./run_toolbox.py watsonx_serving capture_state {namespace} > /dev/null")
