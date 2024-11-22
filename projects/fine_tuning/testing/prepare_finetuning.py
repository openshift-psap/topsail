import os
import pathlib
import logging

from projects.core.library import env, config, run, configure_logging, export
from projects.rhods.library import prepare_rhoai as prepare_rhoai_mod
from projects.gpu_operator.library import prepare_gpu_operator
from projects.matrix_benchmarking.library import visualize

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))

def prepare():
    with run.Parallel("prepare1") as parallel:
        parallel.delayed(prepare_rhoai)
        parallel.delayed(cluster_scale_up)


    test_settings = config.project.get_config("tests.fine_tuning.test_settings")
    with run.Parallel("prepare2") as parallel:
        parallel.delayed(prepare_gpu)
        parallel.delayed(prepare_namespace, test_settings)


def prepare_gpu():
    if not config.project.get_config("gpu.prepare_cluster"):
        return

    prepare_gpu_operator.prepare_gpu_operator()

    if config.project.get_config("clusters.sutest.compute.dedicated"):
        toleration_key = config.project.get_config("clusters.sutest.compute.machineset.taint.key")
        toleration_effect = config.project.get_config("clusters.sutest.compute.machineset.taint.effect")
        prepare_gpu_operator.add_toleration(toleration_effect, toleration_key)

    prepare_gpu_operator.wait_ready(enable_time_sharing=False, wait_stack_deployed=False, wait_metrics=False)


def prepare_rhoai():
    if not PSAP_ODS_SECRET_PATH.exists():
        raise RuntimeError(f"Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")

    token_file = PSAP_ODS_SECRET_PATH / config.project.get_config("secrets.brew_registry_redhat_io_token_file")
    prepare_rhoai_mod.install(token_file)

    has_dsc = run.run("oc get dsc -oname", capture_stdout=True).stdout
    run.run_toolbox(
        "rhods", "update_datasciencecluster",
        enable=["kueue", "codeflare", "trainingoperator", "ray"],
        name=None if has_dsc else "default-dsc",
    )

    if not config.project.get_config("rhods.operator.stop"):
        return

    operator_name = "opendatahub-operator-controller-manager" if config.project.get_config("rhods.catalog.opendatahub") else "rhods-operator"
    run.run(f"oc scale deploy/{operator_name} --replicas=0 -n redhat-ods-operator")
    time.sleep(10)

    if kueue_image := config.project.get_config("rhods.operator.kueue_image"):
        run.run(f"oc set image deploy/kueue-controller-manager training-operator={kueue_image} -n redhat-ods-applications")

    if kto_image := config.project.get_config("rhods.operator.kto_image"):
        run.run(f"oc set image deploy/kubeflow-training-operator manager={kto_image} -n redhat-ods-applications")


def set_namespace_annotations():
    metal = config.project.get_config("clusters.sutest.is_metal")
    dedicated = config.project.get_config("clusters.sutest.compute.dedicated")
    namespace = config.project.get_config("tests.fine_tuning.namespace")

    if metal:
        logging.info("Running in a bare-metal environment, not setting the namespace node-isolation annotations")
        return

    if not dedicated:
        logging.info("Running without dedicated nodes, not setting the namespace node-isolation annotations")
        return

    if config.project.get_config("tests.dry_mode"):
        logging.info("tests.dry_mode is not, skipping setting the node-isolation namespace annotation")
        return

    extra = dict(project=namespace)
    run.run_toolbox_from_config("cluster", "set_project_annotation", prefix="sutest", suffix="scale_test_node_selector", extra=extra, mute_stdout=True)
    run.run_toolbox_from_config("cluster", "set_project_annotation", prefix="sutest", suffix="scale_test_toleration", extra=extra, mute_stdout=True)


def download_data_sources(test_settings):
    namespace = config.project.get_config("tests.fine_tuning.namespace")
    model_name = test_settings.get("model_name")
    dataset_name = test_settings.get("dataset_name")

    pvc_name = config.project.get_config("fine_tuning.pvc.name")
    sources = config.project.get_config(f"fine_tuning.sources")

    dry_mode = config.project.get_config("tests.dry_mode")

    sources_name = []
    if dataset_name:
        sources_name.append(dataset_name)

    if config.project.get_config("tests.fine_tuning.multi_model.enabled"):
        multi_models = config.project.get_config("tests.fine_tuning.multi_model.models")
        for model in multi_models:
            sources_name.append(model["name"])
    if model_name is None:
        pass # nothing to do
    elif isinstance(model_name, str):
        sources_name.append(model_name)
    elif isinstance(model_name, list):
        sources_name += model_name
    else:
        msg = f"Received an unexpected value of 'model_name': {model_name} ({model_name.__class__.__name__})"
        logging.error(msg)
        raise ValueError(msg)

    if not sources_name:
        logging.info("download_data_sources: Nothing to download.")
        return # nothing to do

    if not pvc_name:
        msg = f"Found {len(sources_name)} sources to download, but fine_tuning.pvc.name={pvc_name}"
        logging.error(msg)
        raise ValueError(msg)

    def do_download(extra, secret_key=None, image_key=None):
        name = extra["name"]
        if pvc_name in run.run(f"oc get pvc -n {namespace} -oname -l{name}=yes", check=False, capture_stdout=True).stdout:
            logging.info(f"PVC {pvc_name} already has data source '{name}'. Not downloading it again.")
            return

        logging.info(f"PVC {pvc_name} does not container data source '{name}'. Downloading it ...")

        # ---

        if image_key:
            extra["image"] = config.project.get_config(image_key)

        if secret_key:
            env_key = config.project.get_config("secrets.dir.env_key")
            cred_file = pathlib.Path(os.environ[env_key]) / config.project.get_config(secret_key)
            if not cred_file.exists():
                msg = f"Credential file '{cred_file}' does not exist (${env_key} / *{secret_key})"
                logging.error(msg)
                raise ValueError(msg)

            extra["creds"] = str(cred_file)

        if dry_mode:
            logging.info(f"tests.dry_mode is not, skipping running download_to_pvc({extra})")
            return

        run.run_toolbox_from_config("storage", "download_to_pvc", extra=extra)


    def download_from_source(source_name):
        if source_name not in sources:
            msg = f"Source '{source_name}' not in {', '.join(sources.keys())} ..."
            logging.error(msg)
            raise ValueError(msg)

        source = sources[source_name]["source_dir"].rstrip("/") + "/" + source_name
        storage_dir = "/" + sources[source_name]["type"]
        extra = dict(source=source, storage_dir=storage_dir, name=source_name)

        do_download(
            extra,
            secret_key=sources[source_name].get("secret_key", None),
            image_key=sources[source_name].get("download_pod_image_key", None),
        )


    def download_from_registry(registry_source_name):
        source_name, found, registry_name = registry_source_name.partition("@")
        if not found:
            registry_name = config.project.get_config("fine_tuning.model_registry")
            if not registry_name:
                raise ValueError("Registry not specified :/")

        registry = sources[registry_name]

        source = registry["source_dir"] + source_name
        storage_dir = "/" + registry["registry_type"]
        name = get_safe_model_name(source_name)
        extra = dict(source=source, storage_dir=storage_dir, name=name)

        do_download(
            extra,
            secret_key=registry.get("secret_key", None),
            image_key=registry.get("download_pod_image_key", None),
        )


    for source_name in sources_name:
        if "@" in source_name or (config.project.get_config("fine_tuning.model_registry") and source_name not in sources):
            download_from_registry(source_name)
        else:
            download_from_source(source_name)


def get_safe_model_name(origin_model_name):
    if "@" in origin_model_name:
        model_name, _, _registry_name = origin_model_name.partition("@")
    else:
        model_name = origin_model_name

    return pathlib.Path(model_name).name.lower().replace("_", "-")


def prepare_namespace(test_settings):
    namespace = config.project.get_config("tests.fine_tuning.namespace")
    dry_mode = config.project.get_config("tests.dry_mode")

    if run.run(f'oc get project "{namespace}" 2>/dev/null', check=False).returncode != 0:
        run.run(f'oc new-project "{namespace}" --skip-config-write >/dev/null')
    else:
        logging.warning(f"Project {namespace} already exists.")

    with env.NextArtifactDir("prepare_namespace"):
        set_namespace_annotations()

    with run.Parallel("prepare_data") as parallel:
        parallel.delayed(download_data_sources, test_settings)
        parallel.delayed(preload_image)

    if not dry_mode:
        run.run(f"oc delete pytorchjobs -n {namespace} --all")
        run.run(f"oc delete cm -n {namespace} -ltopsail.fine-tuning-jobname")

    if not config.project.get_config("tests.fine_tuning.many_model.enabled"):
        return

    from projects.scheduler.testing.prepare import prepare_kueue_queue
    local_kueue_name = config.project.get_config("tests.fine_tuning.many_model.kueue_name")

    prepare_kueue_queue(False, namespace, local_kueue_name)


def cluster_scale_up():
    if config.project.get_config("clusters.sutest.is_metal"):
        return

    node_count = config.project.get_config("clusters.sutest.compute.machineset.count")

    if node_count is None:
        logging.info("clusters.sutest.compute.machineset.count isn't set. Not touching the cluster scale.")
        return

    extra = dict(scale=node_count)
    run.run_toolbox_from_config("cluster", "set_scale", prefix="sutest", extra=extra, artifact_dir_suffix="_sutest")


def cleanup_rhoai(mute=True):
    prepare_rhoai_mod.uninstall(mute)


def cleanup_cluster():
    with env.NextArtifactDir("cleanup_cluster"):
        cleanup_sutest_ns()
        cluster_scale_down(to_zero=True)

        cleanup_rhoai()


def cleanup_sutest_ns():
    namespace = config.project.get_config("tests.fine_tuning.namespace")
    # do not delete it ... (to save the PVC)
    # empty the namespace


def cluster_scale_down(to_zero=None):
    if config.project.get_config("clusters.sutest.is_metal"):
        return

    if config.project.get_config("clusters.sutest.compute.machineset.count") is None:
        logging.info("clusters.sutest.compute.machineset.count isn't set. Not touching the cluster scale.")
        return

    machineset_name = config.project.get_config("clusters.sutest.compute.machineset.name")
    has_machineset = run.run(f"oc get machineset {machineset_name} -n openshift-machine-api -oname --ignore-not-found", capture_stdout=True).stdout
    if not has_machineset:
        logging.info(f"No {machineset_name} machineset. Nothing to scale down.")
        return

    if to_zero:
        replicas = 0
    else:
        replicas = config.project.get_config("clusters.sutest.compute.machineset.rest_count")
        if replicas is None: replicas = 1

    run.run(f"oc scale --replicas={replicas} machineset/{machineset_name} -n openshift-machine-api")


def preload_image():
    if config.project.get_config("clusters.sutest.is_metal"):
        return

    RETRIES = 3
    for i in range(RETRIES):
        try:
            run.run_toolbox_from_config("cluster", "preload_image", prefix="sutest")

            break
        except Exception:
            logging.warning(f"Image preloading try #{i+1}/{RETRIES} failed :/")
            if i+1 == RETRIES:
                raise
