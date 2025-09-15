import tempfile
import os
import platform
import prepare
from projects.core.library import config
from projects.core.library import run
import remote_access
import logging
from types import SimpleNamespace
from pathlib import Path
__keep_open = []


def get_tmp_fd():
    fd, file_path = tempfile.mkstemp()

    if platform.system() == "Linux":
        os.remove(file_path)
        py_file = os.fdopen(fd, 'w')
        __keep_open.append(py_file)
        return f"/proc/{os.getpid()}/fd/{fd}", py_file
    else:
        # For macOS and other platforms, return the actual file path
        py_file = os.fdopen(fd, 'w')
        __keep_open.append((file_path, py_file))
        return file_path, py_file


def prepare_gv_from_gh_binary(base_work_dir):

    podman_path, _ = _get_repo_podman_path(base_work_dir)
    gvisor_path = podman_path.parent.parent / "libexec" / "podman" / "gvproxy"

    if remote_access.exists(gvisor_path):
        logging.info("gvproxy exists, not downloading it.")
        return

    src_file = config.project.get_config("prepare.podman.gvisor.repo.file")

    source = "/".join([
        config.project.get_config("prepare.podman.gvisor.repo.url"),
        "releases/download",
        config.project.get_config("prepare.podman.gvisor.repo.version"),
        src_file,
    ])

    result = run.run_toolbox(
        "remote", "download",
        source=source,
        dest=gvisor_path,
        executable=True,
    )

    if result.returncode != 0:
        logging.error(f"Failed to download gvproxy from {source}")
        raise RuntimeError("gvproxy download failed")


def prepare_podman_from_gh_binary(base_work_dir):
    system = config.project.get_config("remote_host.system")

    podman_path, version = _get_repo_podman_path(base_work_dir)

    if remote_access.exists(podman_path):
        logging.info(f"podman {version} already exists, not downloading it.")
        return podman_path

    zip_file = config.project.get_config(f"prepare.podman.repo.{system}.file")

    source = "/".join([
        config.project.get_config("prepare.podman.repo.url"),
        "releases/download",
        config.project.get_config("prepare.podman.repo.version"),
        zip_file,
    ])

    dest = base_work_dir / f"podman-{version}" / zip_file

    run.run_toolbox(
        "remote", "download",
        source=source,
        dest=dest,
        zip=True,
    )

    return podman_path


def _get_repo_podman_path(base_work_dir):
    version = config.project.get_config("prepare.podman.repo.version", print=False)

    podman_path = base_work_dir / f"podman-{version}" / "usr" / "bin" / "podman"

    return podman_path, version


def cleanup_podman_files(base_work_dir):
    version = config.project.get_config("prepare.podman.repo.version", print=False)

    dest = base_work_dir / f"podman-{version}"

    if remote_access.exists(dest):
        logging.info(f"Removing {dest} ...")
        remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -rf {dest}")

    dest = base_work_dir / "podman-custom"

    if remote_access.exists(dest):
        logging.info(f"Removing {dest} ...")
        remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -rf {dest}")


def parse_platform(platform_str):
    p = SimpleNamespace()
    platform_parts = platform_str.split("/")
    if len(platform_parts) != 2:
        raise ValueError(
            f"Invalid platform format: {platform_str}. Expected format is 'container_engine/platform'.")
    p.container_engine = platform_parts[0]
    p.platform = platform_parts[1]

    if p.container_engine not in ["podman", "docker"]:
        raise ValueError(f"Unsupported container engine: {p.container_engine}. Expected 'podman' or 'docker'.")
    if p.platform not in ["darwin"]:  # TODO: Implement "linux", "windows"
        raise ValueError(f"Unsupported platform: {p.platform}.")

    if p.container_engine == "podman":
        p.prepare_platform = prepare.prepare_podman_platform_darwin
        p.cleanup_platform = prepare.cleanup_podman_platform_darwin
    elif p.container_engine == "docker":
        p.prepare_platform = prepare.prepare_docker_platform_darwin
        p.cleanup_platform = prepare.cleanup_docker_platform_darwin

    return p


def parse_benchmark(benchmark_name):
    b = SimpleNamespace()
    supported_container_engines = config.project.get_config(
        f"{benchmark_name}.supported_container_engines",
        print=False)
    if not supported_container_engines:
        raise ValueError(f"Benchmark '{benchmark_name}' is not supported or has no runtimes defined.")
    b.name = benchmark_name
    if isinstance(supported_container_engines, str):
        supported_container_engines = [supported_container_engines]
    b.supported_container_engines = supported_container_engines

    raw_runs = config.project.get_config(
        f"{benchmark_name}.runs",
        print=False)
    try:
        runs = int(raw_runs)
    except (TypeError, ValueError):
        raise ValueError(f"Benchmark '{benchmark_name}' has an invalid 'runs' value: {raw_runs!r}.")
    if runs < 1:
        raise ValueError(f"Benchmark '{benchmark_name}' must have runs >= 1 (got {runs}).")
    b.runs = runs
    return b


def get_benchmark_script_path(base_work_dir):
    return base_work_dir / "utils" / "exec_time.py"


def prepare_benchmark_script(base_work_dir):

    dest = get_benchmark_script_path(base_work_dir)

    source = Path(__file__).parent.resolve() / "exec_time.py"

    if not source.exists():
        raise FileNotFoundError(f"Benchmark script not found at {source}")

    run.run_toolbox(
        "container_bench", "prepare_benchmark_script_on_remote",
        source=source,
        dest=dest,
    )

    return dest


def prepare_custom_podman_binary(base_work_dir):
    dest_dir = base_work_dir / "podman-custom"

    bin_dir = Path(config.project.get_config("prepare.podman.custom_binary.path"))

    if not bin_dir.exists():
        raise FileNotFoundError(f"Custom podman binary not found at {bin_dir}")

    client_file = config.project.get_config("prepare.podman.custom_binary.client_file")
    server_file = config.project.get_config("prepare.podman.custom_binary.server_file")
    source_client = bin_dir / client_file
    if not source_client.exists():
        raise FileNotFoundError(f"Custom podman client binary not found at {source_client}")

    source_server = bin_dir / server_file
    if not source_server.exists():
        raise FileNotFoundError(f"Custom podman server binary not found at {source_server}")

    run.run_toolbox(
        "container_bench", "copy_file",
        source=source_client,
        dest=dest_dir / client_file,
    )

    run.run_toolbox(
        "container_bench", "copy_file",
        source=source_server,
        dest=dest_dir / server_file,
    )

    return dest_dir / client_file
