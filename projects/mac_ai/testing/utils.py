import tempfile
import os
import types
import pathlib
import requests

from projects.core.library import env, config, run, configure_logging, export

import remote_access

__keep_open = []
def get_tmp_fd():
    # generate a fd-only temporary file
    fd, file_path = tempfile.mkstemp()

    # using only the FD. Ensures that the file disappears when this
    # process terminates
    os.remove(file_path)

    py_file = os.fdopen(fd, 'w')
    # this makes sure the FD isn't closed when the var goes out of
    # scope
    __keep_open.append(py_file)

    return f"/proc/{os.getpid()}/fd/{fd}", py_file

def parse_platform(platform_str):
    platform = types.SimpleNamespace()

    platform_parts = platform_str.split("/")
    if not len(platform_parts) >= 2:
        raise ValueError(f"Invalid platform string: {platform_str}. Expected at least <system>/>inference_server_name>")

    platform.system = platform_parts.pop(0)
    platform.inference_server_name = platform_parts.pop(0)

    expected_systems = config.project.get_config("__platform_check.system", print=False)
    if not platform.system in expected_systems:
        raise ValueError(f"Invalid platform system '{platform.system}' in {platform_str}. Expected one of {expected_systems}")

    expected_servers = config.project.get_config("__platform_check.inference_server", print=False)
    if not platform.inference_server_name in expected_servers:
        raise ValueError(f"Invalid platform inference server '{platform.inference_server_name}' in {platform_str}. Expected one of {expected_servers}")

    # too complex to put in the configuration file!
    if platform.inference_server_name in ("ramalama", "lightspeed"):
        platform.needs_podman_machine = True
        platform.needs_podman= False
    else:
        platform.needs_podman = platform.system == "podman"
        platform.needs_podman_machine = platform.needs_podman

    inference_server_has_flavors = config.project.get_config("__platform_check.flavors", print=False).get(platform.inference_server_name)

    if not inference_server_has_flavors:
        platform.inference_server_flavor = None
    else:
        platform.inference_server_flavor = platform_parts.pop(-1) \
            if platform_parts else None

        if platform.inference_server_flavor not in inference_server_has_flavors:
            raise ValueError(f"Invalid platform inference server flavor ({platform.inference_server_flavor}) in {platform_str}. Expected one of {inference_server_has_flavors}")


    no_gpu_option_name = config.project.get_config("__platform_check.options.no_gpu", print=False)
    if no_gpu_option_name in platform_parts:
        platform.want_gpu = False
        platform_parts.remove(no_gpu_option_name)
    elif platform.inference_server_flavor == no_gpu_option_name:
        platform.want_gpu = False
    else:
        platform.want_gpu = True

    platform.name = platform_str

    import prepare_mac_ai
    platform.inference_server_mod = prepare_mac_ai.INFERENCE_SERVERS.get(platform.inference_server_name)
    platform.prepare_inference_server_mod = prepare_mac_ai.PREPARE_INFERENCE_SERVERS.get(platform.inference_server_name)

    if not (platform.prepare_inference_server_mod and platform.inference_server_mod):
        msg = (f"Inference server ({platform.inference_server_name}) incorrectly configured :/. "
               f"Expected one of {', '.join(prepare_mac_ai.INFERENCE_SERVERS)}")
        logging.fatal(msg)
        raise ValueError(msg)

    if platform_parts:
        raise ValueError(f"Couldn't parse '{platform_parts}' in the platform specification '{platform_str}' :/")

    return platform


def check_expected_platform(
        platform,
        system=None,
        needs_podman=None,
        needs_podman_machine=None,
        inference_server_name=None,
        inference_server_flavor=None,
):
    kwargs = dict(
        system=system,
        needs_podman=needs_podman,
        needs_podman_machine=needs_podman_machine,
        inference_server_name=inference_server_name,
        inference_server_flavor=inference_server_flavor,
    )

    errors = []
    for k, v in kwargs.items():
        if not v: continue
        platform_value = platform.__dict__[k]
        if platform_value == v: continue
        errors.append(f"Invalid {k}: expected {v}, got {platform_value}")

    return ". ".join(errors)


def model_to_fname(model):
    base_work_dir = remote_access.prepare()
    model_gguf_dir = config.project.get_config("test.model.gguf_dir")
    return base_work_dir / model_gguf_dir / pathlib.Path(model).name

def get_latest_release(repo_url):
    prefix, found, path = repo_url.partition("https://github.com/")
    if not found:
        raise ValueError(f"utils.get_latest_release expects a github repo. Got {repo_url} ...")

    url = f"https://api.github.com/repos/{path}/releases/latest"
    resp = requests.get(url)
    data = resp.json()
    return data["name"]
