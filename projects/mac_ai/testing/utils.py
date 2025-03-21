import tempfile
import os
import types

from projects.core.library import env, config, run, configure_logging, export


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

    platform.system = platform_parts.pop(0)
    platform.inference_server_name = platform_parts.pop(0)

    expected_systems = config.project.get_config("__platform_check.system", print=False)
    if not platform.system in expected_systems:
        raise ValueError(f"Invalid platform system ({platform.system}) in {platform_str}. Expected one of {expected_systems}")

    expected_servers = config.project.get_config("__platform_check.inference_server", print=False)
    if not platform.inference_server_name in expected_servers:
        raise ValueError(f"Invalid platform inference server ({platform.inference_server_name}) in {platform_str}. Expected one of {expected_servers}")

    platform.needs_podman = platform.system in config.project.get_config("__platform_check.system_needs_podman", print=False)

    inference_server_has_flavors = config.project.get_config("__platform_check.flavors", print=False).get(platform.inference_server_name)

    if not inference_server_has_flavors:
        platform.inference_server_flavor = None
    else:
        platform.inference_server_flavor = platform_parts.pop(-1)
        if not platform.inference_server_flavor in inference_server_has_flavors:
            raise ValueError(f"Invalid platform inference server flavor ({platform.inference_server_flavor}) in {platform_str}. Expected one of {inference_server_has_flavors}")

    no_gpu_option_name = config.project.get_config("__platform_check.options.no_gpu", print=False)
    if no_gpu_option_name in platform_parts:
        platform.podman_no_gpu = True
        platform_parts.remove(no_gpu_option_name)
    else:
        platform.podman_no_gpu = False

    platform.name = platform_str

    import prepare_mac_ai
    platform.inference_server_mod = prepare_mac_ai.INFERENCE_SERVERS.get(platform.inference_server_name)
    platform.prepare_inference_server_mod = prepare_mac_ai.PREPARE_INFERENCE_SERVERS.get(platform.inference_server_name)

    if not (platform.prepare_inference_server_mod and platform.inference_server_mod):
        msg = (f"Inference server ({platform.inference_server_name}) incorrectly configured :/. "
               f"Expected one of {', '.join(INFERENCE_SERVERS)}")
        logging.fatal(msg)
        raise ValueError(msg)

    if platform_parts:
        raise ValueError(f"Couldn't parse '{platform_parts}' in the platform specification '{platform_str}' :/")

    return platform


def check_expected_platform(
        platform,
        system=None,
        needs_podman=None,
        inference_server_name=None,
        inference_server_flavor=None,
):
    kwargs = dict(
        system=system,
        needs_podman=needs_podman,
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
