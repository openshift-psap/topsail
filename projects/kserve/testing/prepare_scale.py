import logging
import pathlib
import os
import yaml

from topsail.testing import env, config, run, prepare_gpu_operator, prepare_user_pods, prepare_gpu_operator, merge_dicts, sizing
import prepare_kserve

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent

def prepare_gpu():
    if not config.ci_artifacts.get_config("gpu.prepare_cluster"):
        return

    prepare_gpu_operator.prepare_gpu_operator()

    if config.ci_artifacts.get_config("clusters.sutest.compute.dedicated"):
        toleration_key = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.taint.key")
        toleration_effect = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.taint.effect")
        prepare_gpu_operator.add_toleration(toleration_effect, toleration_key)

    prepare_gpu_operator.wait_ready()


def prepare():
    """
    Prepares the cluster and the namespace for running the KServe scale tests
    """

    test_mode = config.ci_artifacts.get_config("tests.mode")
    if test_mode == "scale":
        consolidate_model_config("tests.scale.model")
        config.ci_artifacts.set_config("tests.scale.model.consolidated", True)
        user_count = config.ci_artifacts.get_config("tests.scale.namespace.replicas")
    elif test_mode in ("e2e", "prepare_only"):
        user_count = len(config.ci_artifacts.get_config("tests.e2e.models"))
    else:
        raise KeyError(f"Invalid test mode: {test_mode}")

    prepare_user_pods.apply_prefer_pr()

    with run.Parallel("prepare_scale") as parallel:
        # prepare the sutest cluster
        parallel.delayed(prepare_kserve.prepare)
        parallel.delayed(scale_up_sutest)

        # prepare the driver cluster
        namespace = config.ci_artifacts.get_config("base_image.namespace")

        parallel.delayed(prepare_user_pods.prepare_user_pods, user_count)
        parallel.delayed(prepare_user_pods.cluster_scale_up, user_count)

    # must be after prepare_kserve.prepare and before prepare_kserve.preload_image
    # must not be in a parallel group, because it updates the config file
    prepare_kserve.update_serving_runtime_images()

    with run.Parallel("prepare_scale2") as parallel:
        # must be after prepare_kserve.update_serving_runtime_images
        parallel.delayed(prepare_kserve.preload_image)
        # must be after scale_up_sutest
        parallel.delayed(prepare_gpu)


def scale_compute_sutest_node_requirement():
    ns_count = config.ci_artifacts.get_config("tests.scale.namespace.replicas")
    models_per_ns = config.ci_artifacts.get_config("tests.scale.model.replicas")
    models_count = ns_count * models_per_ns

    cpu_rq = config.ci_artifacts.get_config("tests.scale.model.serving_runtime.kserve.resource_request.cpu") + config.ci_artifacts.get_config("tests.scale.model.serving_runtime.kserve.resource_request.cpu")
    mem_rq = config.ci_artifacts.get_config("tests.scale.model.serving_runtime.transformer.resource_request.memory") + config.ci_artifacts.get_config("tests.scale.model.serving_runtime.transformer.resource_request.memory")

    kwargs = dict(
        cpu = cpu_rq,
        memory = mem_rq,
        machine_type = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.type"),
        user_count = models_count,
        )

    machine_count = sizing.main(**kwargs)

    # the sutest Pods must fit in one machine.
    return min(models_count, machine_count)


def e2e_compute_sutest_node_requirement():
    if config.ci_artifacts.get_config("tests.e2e.mode") == "single":
        return 1

    return len(config.ci_artifacts.get_config("tests.e2e.models"))

def scale_up_sutest():
    if config.ci_artifacts.get_config("clusters.sutest.is_metal"):
        return

    test_mode = config.ci_artifacts.get_config("tests.mode")
    node_count = config.ci_artifacts.get_config("clusters.sutest.compute.machineset.count")
    if node_count is not None:
        logging.info(f"Using the sutest node count from the configuration: {node_count}")
    elif test_mode == "scale":
        node_count = scale_compute_sutest_node_requirement()
    elif test_mode in ("e2e", "prepare_only"):
        node_count = e2e_compute_sutest_node_requirement()
    else:
        raise KeyError(f"Invalid test mode: {test_mode}")

    extra = dict(scale=node_count)
    run.run_toolbox_from_config("cluster", "set_scale", prefix="sutest", extra=extra, artifact_dir_suffix="_sutest")


def cluster_scale_up():
    namespace = config.ci_artifacts.get_config("base_image.namespace")
    user_count = config.ci_artifacts.get_config("tests.scale.namespace.replicas")

    with run.Parallel("cluster_scale_up") as parallel:
        parallel.delayed(prepare_user_pods.cluster_scale_up, user_count)
        parallel.delayed(scale_up_sutest)


def cluster_scale_down(to_zero=False):
    if config.ci_artifacts.get_config("clusters.sutest.is_metal"):
        return

    extra = dict(scale=0 if to_zero else 1)
    with run.Parallel("cluster_scale_down") as parallel:
        parallel.delayed(run.run_toolbox_from_config, "cluster", "set_scale", prefix="sutest", extra=extra)
        parallel.delayed(run.run_toolbox_from_config, "cluster", "set_scale", prefix="driver", extra=extra)


def get_file_config(file_model_name):
    with open(TESTING_THIS_DIR / "models" / f"{file_model_name}.yaml") as f:
        return yaml.safe_load(f)


def get_base_config(model_name):
    # base = testing/models/<model_name>
    base_config = get_file_config(model_name)

    extends_name = base_config.pop("extends", False)
    if not extends_name: return base_config # end of recusion

    config_to_extend = get_base_config(extends_name) # recursive call

    return merge_dicts(config_to_extend, base_config)


def consolidate_model_config(config_location=None, _model_name=None, index=None, show=True):
    # test = <config_location>
    test_config = config.ci_artifacts.get_config(config_location) if config_location \
        else {}

    model_name = _model_name or test_config.get("name")
    if isinstance(model_name, dict):
        __model_name = list(model_name.keys())[0]
        test_config = merge_dicts(test_config, model_name[__model_name])
        model_name = test_config.get("name")
        test_config["name"] = __model_name
    else:
        test_config["name"] = model_name

    if not model_name:
        raise RuntimeError(f"Couldn't find a name for consolidating the model configuration ... {config_location}={test_config} and model_name={_model_name}")

    if model_name == "help":
        logging.info("")
        logging.info("Available models:")
        for a_model_name in (TESTING_THIS_DIR / "models").glob("*.yaml"):
            logging.info(f"- {a_model_name.stem}")

        raise SystemExit(0)

    model_directory_prefix = config.ci_artifacts.get_config("kserve.model.directory_prefix")
    if model_directory_prefix:
        model_name = model_directory_prefix + "/" + model_name

    base_config = get_base_config(model_name)

    # kserve_model = config(kserve.model)
    kserve_model_config = config.ci_artifacts.get_config("kserve.model")

    # model = base
    model_config = base_config
    # model += kserve_model
    model_config = merge_dicts(model_config, kserve_model_config)
    # base += test
    model_config = merge_dicts(model_config, test_config)

    if index is not None:
        model_config["index"] = index

    if config_location:
        config.ci_artifacts.set_config(config_location, model_config)

    if show:
        dump = yaml.dump(model_config,  default_flow_style=False, sort_keys=False).strip()
        logging.info(f"Consolidated configuration for model '{model_name}':\n{dump}")

    return model_config
