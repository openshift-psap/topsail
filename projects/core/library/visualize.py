#! /usr/bin/env python

import pathlib
import shutil
import sys
import functools
import subprocess
import os
import yaml, json
import logging
logging.getLogger().setLevel(logging.INFO)

import fire

from projects.core.library import env, config, run

TOPSAIL_DIR = pathlib.Path(config.__file__).parents[3]

matbench_config = None # will be set in init()
matbench_workload = None # will be set in init()
workload_storage_dir = None # will be set in init()


def init(allow_no_config_file=False):
    global matbench_config, matbench_workload, workload_storage_dir

    env.init()
    config_file = os.environ.get("CI_ARTIFACTS_FROM_CONFIG_FILE")
    if not config_file and not allow_no_config_file:
        raise RuntimeError("CI_ARTIFACTS_FROM_CONFIG_FILE must be set. Please source your `configure.sh` before running this file.")

    if not config_file:
        logging.info("Running without CI_ARTIFACTS_FROM_CONFIG_FILE, skipping most of the initialization")
        return

    config.init(pathlib.Path(config_file).parent)

    is_plot_test = config.ci_artifacts.get_config("PR_POSITIONAL_ARG_0", "", warn=False).endswith("-plot")
    if is_plot_test:
        pr_arg_1 = config.ci_artifacts.get_config("PR_POSITIONAL_ARG_1", "")
        if not pr_arg_1:
            raise ValueError("PR_POSITIONAL_ARG_1 should have been set ...")

        config.ci_artifacts.set_config("matbench.preset", pr_arg_1, dump_command_args=False)

    matbench_workload = config.ci_artifacts.get_config("matbench.workload")

    workload_storage_dir = pathlib.Path(matbench_workload.replace(".", "/"))

    if is_plot_test:
        config.ci_artifacts.set_config("matbench.preset", config.ci_artifacts.get_config("PR_POSITIONAL_ARG_1", None), dump_command_args=False)

    matbench_preset = config.ci_artifacts.get_config("matbench.preset")
    if not matbench_preset:
        pass # no preset defined, nothing to do
    elif "://" in str(matbench_preset):
        config.ci_artifacts.set_config("matbench.download.url", matbench_preset, dump_command_args=False)
    else:
        config.ci_artifacts.set_config("matbench.config_file", f"{matbench_preset}.yaml", dump_command_args=False)
        config.ci_artifacts.set_config("matbench.download.url_file", workload_storage_dir / "data" / f"{matbench_preset}.yaml", dump_command_args=False)

    matbench_config = config.Config(workload_storage_dir / "data" / config.ci_artifacts.get_config("matbench.config_file"))


def entrypoint(allow_no_config_file=False):
    def decorator(fct):
        @functools.wraps(fct)
        def wrapper(*args, **kwargs):
            init(allow_no_config_file)
            fct(*args, **kwargs)

        return wrapper
    return decorator


@entrypoint(allow_no_config_file=True)
def prepare_matbench():

    run.run(f"""
    pip install --quiet --requirement "{TOPSAIL_DIR}/projects/core/subprojects/matrix-benchmarking/requirements.txt"
    """)


@entrypoint()
def generate_visualizations(results_dirname, generate_lts=None):
    visualizations = matbench_config.get_config("visualize")
    plotting_failed = False
    for idx in range(len(visualizations)):
        generate_visualization(results_dirname, idx, generate_lts=generate_lts)

    if plotting_failed:
        raise RuntimeError("Som of visualization failed")


def call_parse(step_idx, common_args, common_env):
    parse_env = common_env.copy()
    parse_args = common_args.copy()

    mode = config.ci_artifacts.get_config("matbench.download.mode")
    if mode != "prefer_cache":
        logging.info(f"Download mode set to '{mode}', ignoring the parser cache.")
        parse_env["MATBENCH_STORE_IGNORE_CACHE"] = "y"

    parse_args["output-matrix"] = env.ARTIFACT_DIR / "internal_matrix.json"

    parse_args_str = " ".join(f"'--{k}={v}'" for k, v in parse_args.items())
    parse_env_str = "env " + " ".join(f"'{k}={v}'" for k, v in parse_env.items())

    log_file = env.ARTIFACT_DIR / f"{step_idx}_matbench_parse.log"

    cmd = f"{parse_env_str} matbench parse {parse_args_str} |& tee > {log_file}"

    errors = []
    if run.run(cmd, check=False).returncode != 0:
        logging.warning("An error happened while parsing the results  ...")
        errors.append(log_file.name)

    if log_has_errors(log_file):
        logging.warning("Errors detected in the log file. Not aborting the processing.")

    return errors

def call_generate_lts(step_idx, common_args, common_env_str):
    lts_args = common_args.copy()
    lts_args["output-lts"] = env.ARTIFACT_DIR / "lts_payload.json"
    lts_args_str = " ".join(f"'--{k}={v}'" for k, v in lts_args.items())

    log_file = env.ARTIFACT_DIR / f"{step_idx}_matbench_generate_lts.log"

    cmd = f"{common_env_str} matbench parse {lts_args_str} |& tee > {log_file}"

    errors = []
    if run.run(cmd, check=False).returncode != 0:
        logging.warning("An error happened while generating the LTS payload ...")
        errors.append(log_file.name)

    if log_has_errors(log_file):
        errors.append(log_file.name)

    return errors


def call_generate_lts_schema(step_idx, common_args):
    lts_schema_args = common_args.copy()

    lts_schema_args.pop("results_dirname")
    lts_schema_args["file"] = env.ARTIFACT_DIR / "lts_payload.schema.json"
    lts_schema_args_str = " ".join(f"'--{k}={v}'" for k, v in lts_schema_args.items())

    log_file = env.ARTIFACT_DIR / f"{step_idx}_matbench_generate_lts_schema.log"

    cmd = f"matbench generate_lts_schema {lts_schema_args_str} |& tee > {log_file}"

    errors = []
    if run.run(cmd, check=False).returncode != 0:
        logging.warning("An error happened while generating the LTS payload schema...")
        errors.apprend(log_file.name)

    if log_has_errors(log_file):
        errors.append(log_file.name)

    return errors


def generate_opensearch_config_yaml_env(dest):
    instance = config.ci_artifacts.get_config("matbench.lts.opensearch.instance")

    _index = config.ci_artifacts.get_config("matbench.lts.opensearch.index")
    index_prefix = config.ci_artifacts.get_config("matbench.lts.opensearch.index_prefix") or ""
    index = f"{index_prefix}{_index}"

    vault_key = config.ci_artifacts.get_config("secrets.dir.env_key")
    opensearch_instances_file = config.ci_artifacts.get_config("secrets.opensearch_instances")

    with open(pathlib.Path(os.environ[vault_key]) / opensearch_instances_file) as f:
        instances_file_doc = yaml.safe_load(f)

    env_doc = dict(
        opensearch_username=instances_file_doc[instance]["username"],
        opensearch_password=instances_file_doc[instance]["password"],
        opensearch_port=instances_file_doc[instance]["port"],
        opensearch_host=instances_file_doc[instance]["host"],
        opensearch_index=index,
    )

    with open(dest, "w") as f:
        yaml.dump(env_doc, f, indent=4)


def call_download_lts(step_idx, common_args, common_env_str):
    download_args = common_args.copy()

    download_args["lts_results_dirname"] = pathlib.Path(download_args.pop("results_dirname")) / "lts"

    download_args.pop("workload")
    download_args.pop("workload_base_dir")
    download_args["force"] = True
    download_args["clean"] = True

    download_args_str = " ".join(f"'--{k}={v}'" for k, v in download_args.items())

    log_file = env.ARTIFACT_DIR / f"{step_idx}_matbench_download_lts.log"

    cmd = f"{common_env_str} matbench download_lts {download_args_str} |& tee > {log_file}"

    errors = []
    if run.run(cmd, check=False).returncode != 0:
        logging.warning("An error happened while downloading the LTS payload ...")
        errors.append(log_file.name)

    return errors


def call_upload_lts(step_idx, common_args, common_env_str):
    upload_args = common_args.copy()
    upload_args_str = " ".join(f"'--{k}={v}'" for k, v in upload_args.items())

    log_file = env.ARTIFACT_DIR / f"{step_idx}_matbench_upload_lts.log"

    env_file = pathlib.Path(".env.generated.yaml")
    generate_opensearch_config_yaml_env(env_file)

    cmd = f"{common_env_str} matbench upload_lts {upload_args_str} |& tee > {log_file}"

    errors = []
    if run.run(cmd, check=False).returncode != 0:
        logging.warning("An error happened while uploading the LTS payload ...")
        errors.append(log_file.name)

    env_file.unlink()

    return errors


def call_analyze_lts(step_idx, common_args, common_env_str):
    analyze_args = common_args.copy()
    analyze_args["lts_results_dirname"] = pathlib.Path(analyze_args["results_dirname"]) / "lts"
    analyze_args_str = " ".join(f"'--{k}={v}'" for k, v in analyze_args.items())

    log_file = env.ARTIFACT_DIR / f"{step_idx}_matbench_analyze_lts.log"

    env_file = pathlib.Path(".env.generated.yaml")
    generate_opensearch_config_yaml_env(env_file)

    cmd = f"{common_env_str} matbench analyze_lts {analyze_args_str} |& tee > {log_file}"

    errors = []
    retcode = run.run(cmd, check=False).returncode


    if retcode == 0:
        logging.info("The regression analyses did not detect any regression.")
        regression_detected = False
    elif retcode < 100:
        logging.warning("A regression was detected.")
        regression_detected = True
    else:
        logging.warning("An error happened while analyzing the LTS payload ...")
        errors.append(log_file.name)
        regression_detected = None

    env_file.unlink()

    return errors, regression_detected


def log_has_errors(log_file):
    has_errors = False
    if not log_file.exists():
        logging.error(f"Log file {log_file} does not exist...")
        return True

    with open(log_file) as log_f:
        for line in log_f.readlines():
            if not line.startswith("ERROR"):
                continue

            has_errors = True

            with open(env.ARTIFACT_DIR / "FAILURE", "a") as fail_f:
                print(line, end="", file=fail_f)
                logging.error(line.strip())

    return has_errors


def call_visualize(step_idx, common_env_str, common_args, filters_to_apply, generate_url):
    visu_args = common_args.copy()
    visu_args["filters"] = filters_to_apply
    visu_args["generate"] = generate_url
    visu_args_str = " ".join(f"'--{k}={v}'" for k, v in visu_args.items())

    dest_dir = env.ARTIFACT_DIR / filters_to_apply
    dest_dir.mkdir(parents=True, exist_ok=True)

    log_file = dest_dir / f"{step_idx}_matbench_visualize.log"

    cmd = f"{common_env_str} matbench visualize {visu_args_str} |& tee > {log_file}"

    errors = []
    if run.run(cmd, check=False, cwd=dest_dir).returncode != 0:
        logging.warning("An error happened while generating the visualization ...")
        errors.append(log_file.name)

    if log_has_errors(log_file):
        errors.append(log_file.name)

    run.run(f"""
        mkdir -p {dest_dir}/figures_{{png,html}}
        mv {dest_dir}/fig_*.png "{dest_dir}/figures_png" 2>/dev/null || true
        mv {dest_dir}/fig_*.html "{dest_dir}/figures_html" 2>/dev/null || true
        """)

    return errors


def generate_visualization(results_dirname, idx, generate_lts=None, upload_lts=None, analyze_lts=None):
    generate_list = matbench_config.get_config(f"visualize[{idx}].generate")
    if not generate_list:
        raise ValueError(f"Couldn't get the configuration #{idx} ...")

    generate_url = "stats=" + "&stats=".join(generate_list)

    common_args, common_env = get_common_matbench_args_env(results_dirname)
    common_env_str = "env " + " ".join(f"'{k}={v}'" for k, v in common_env.items())

    step_idx = 0
    errors = []

    #
    # Parse the results, to validate that they are well formed
    #

    errors += call_parse(step_idx, common_args, common_env)

    if errors:
        msg = f"An error happened during the results parsing, aborting the visualization ({', '.join(errors)})."
        with open(env.ARTIFACT_DIR / "FAILURE", "w") as f:
            print(msg, file=f)
        logging.error(msg)
        raise RuntimeError(msg)

    #
    # Save the LTS in the artifacts, to have it along with the other files
    # Save the LTS schema in the artifacts
    #

    do_generate_lts = generate_lts if generate_lts is not None \
        else config.ci_artifacts.get_config("matbench.lts.generate", None)

    if do_generate_lts:
        step_idx += 1
        errors += call_generate_lts(step_idx, common_args, common_env_str)

        step_idx += 1
        errors += call_generate_lts_schema(step_idx, common_args)

    if config.ci_artifacts.get_config("matbench.download.save_to_artifacts"):
        shutil.copytree(common_args["MATBENCH_RESULTS_DIRNAME"], env.ARTIFACT_DIR / "downloaded")

    #
    # Download the historical LTS payloads for comparions
    # Analyze the new results for regression against the historical results
    #

    replotting = config.ci_artifacts.get_config("PR_POSITIONAL_ARG_0", "").endswith("-plot")

    do_analyze_lts = analyze_lts if analyze_lts is not None \
        else config.ci_artifacts.get_config("matbench.lts.regression_analyses.enabled", None)

    if replotting and not config.ci_artifacts.get_config("matbench.lts.regression_analyses.enabled_on_replot", None):
        do_analyze_lts = False

    do_upload_lts = upload_lts if upload_lts is not None \
        else config.ci_artifacts.get_config("matbench.lts.opensearch.export.enabled", None)

    if replotting and not config.ci_artifacts.get_config("matbench.lts.opensearch.export.enabled_on_replot", None):
        do_upload_lts = False

    try:
        env_file = pathlib.Path(".env.generated.yaml")
        generate_opensearch_config_yaml_env(env_file)
    except FileNotFoundError:
        logging.warning(f"Opensearch secret file does not exist: {e}")
        do_analyze_lts = False
        do_upload_lts = False

        fail_on_regression = config.ci_artifacts.get_config("matbench.lts.regression_analyses.fail_test_on_regression")
        fail_on_upload = config.ci_artifacts.get_config("matbench.lts.opensearch.export.fail_test_on_fail")
        if fail_on_upload or fail_on_regression:
            errors += ["opensearch secret missing"]

    if do_analyze_lts:
        step_idx += 1
        download_lts_errors = call_download_lts(step_idx, common_args, common_env_str)
        errors += download_lts_errors

        step_idx += 1
        analyze_lts_errors, regression_detected = call_analyze_lts(step_idx, common_args, common_env_str)
        errors += analyze_lts_errors

        if regression_detected:
            if config.ci_artifacts.get_config("matbench.lts.regression_analyses.fail_test_on_regression"):
                errors += ["regression detected"]
            else:
                logging.warning("A regression has been detected, but ignored as per matbench.lts.regression_analyses.fail_test_on_regression")

    #
    # Upload the LTS payload for future regression analyses
    #

    if do_upload_lts:
        step_idx += 1
        upload_lts_errors = call_upload_lts(step_idx, common_args, common_env_str)
        if config.ci_artifacts.get_config("matbench.lts.opensearch.export.fail_test_on_fail"):
            errors += upload_lts_errors
        elif upload_lts_errors:
            logging.warning("An error happened during the LTS load. Ignoring as per matbench.lts.opensearch.export.fail_test_on_fail.")

    #
    # Generate the visualization reports
    #

    filters = matbench_config.get_config(f"visualize[{idx}]").get("filters", [None])
    for filters_to_apply in filters:
        if not filters_to_apply:
            filters_to_apply = ""

        step_idx += 1
        errors += call_visualize(step_idx, common_env_str, common_args, filters_to_apply, generate_url)

    #
    # Done :)
    #

    if errors:
        msg = f"An error happened during the visualization post-processing ... ({', '.join(errors)})"
        logging.error(msg)
        with open(env.ARTIFACT_DIR / "FAILURE", "w") as f:
            print(msg, file=f)
        raise RuntimeError(msg)


@entrypoint()
def generate_from_dir(results_dirname, generate_lts=None):
    logging.info(f"Generating the visualization from '{results_dirname}' ...")

    generate_visualizations(results_dirname, generate_lts=generate_lts)


def get_common_matbench_args_env(results_dirname):
    common_args = dict()
    common_args["results_dirname"] = results_dirname
    common_args["workload"] = config.ci_artifacts.get_config("matbench.workload")

    common_args["workload_base_dir"] = str(TOPSAIL_DIR)

    common_env = dict()
    common_env["MATBENCH_SIMPLE_STORE_IGNORE_EXIT_CODE"] = "true" if config.ci_artifacts.get_config("matbench.ignore_exit_code") else "false"

    return common_args, common_env


def download(results_dirname):
    url = config.ci_artifacts.get_config("matbench.download.url")
    url_file = config.ci_artifacts.get_config("matbench.download.url_file")

    if url:
        with open(env.ARTIFACT_DIR / "source_url", "w") as f:
            print(url, file=f)

    elif url_file:
        shutil.copyfile(url_file, env.ARTIFACT_DIR / "source_url")
    else:
        raise ValueError("matbench.download.url or matbench.download.url_file must be specified")

    common_args, common_env = get_common_matbench_args_env(results_dirname)

    download_args = common_args.copy()
    download_args |= dict(
        mode=config.ci_artifacts.get_config("matbench.download.mode"),
        do_download=True,
    )

    env_key = config.ci_artifacts.get_config("secrets.dir.env_key")
    secret_path = os.environ.get(env_key)
    secret_filename = config.ci_artifacts.get_config("secrets.aws_credentials")

    if not env_key or not secret_path or not secret_filename:
        logging.warning(f"secrets.dir.env_key or ${secret_path} not set or {secret_filename=}. Cannot set AWS_SHARED_CREDENTIALS_FILE")
    else:
        os.environ["AWS_SHARED_CREDENTIALS_FILE"] = secret_path + "/.awscred"

    if url:
        download_args["url"] = url
    elif url_file:
        download_args["url_file"] = url_file

    download_args_str = " ".join(f"'--{k}={v}'" for k, v in download_args.items())
    common_env_str = "env " + " ".join(f"'{k}={v}'" for k, v in common_env.items())

    run.run(f"{common_env_str} matbench download {download_args_str} |& tee > {env.ARTIFACT_DIR}/_matbench_download.log")


@entrypoint()
def download_and_generate_visualizations(results_dirname="/tmp/matrix_benchmarking_results"):
    prepare_matbench()

    download(results_dirname)

    generate_visualizations(results_dirname)


class Visualize:
    """
    Commands for launching the visualization commands
    """

    def __init__(self):
        self.prepare_matbench = prepare_matbench
        self.generate_visualizations = generate_visualizations
        self.generate_visualizations_from_dir = generate_from_dir
        self.download_and_generate_visualizations = download_and_generate_visualizations


def main():
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    fire.Fire(Visualize())


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{e.cmd}' failed --> {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print() # empty line after ^C
        logging.error(f"Interrupted.")
        sys.exit(1)
