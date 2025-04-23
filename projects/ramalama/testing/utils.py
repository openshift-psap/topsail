import tempfile
import os
import types
import pathlib

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

    if not platform.inference_server_name == "ramalama":
        raise ValueError("Only ramalama can be tested from this project.")

    # too complex to put in the configuration file!
    platform.needs_podman_machine = True
    platform.needs_podman= False
    platform.inference_server_flavor = None
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
