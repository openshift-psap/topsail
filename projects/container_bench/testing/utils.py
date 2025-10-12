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


def prepare_podman_from_gh_binary(base_work_dir):
    system = config.project.get_config("remote_host.system", print=False)

    podman_path, version = _get_repo_podman_path(base_work_dir)

    if remote_access.exists(podman_path):
        logging.info(f"podman {version} already exists, not downloading it.")
        return podman_path

    zip_file = config.project.get_config(f"prepare.podman.repo.{system}.file")
    if system == "linux":
        source = "/".join([
            config.project.get_config("prepare.podman.repo.url"),
            "archive/refs/tags",
            zip_file,
        ])
    else:
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

    if config.project.get_config("remote_host.system", print=False) == "linux":
        podman_path = base_work_dir / f"podman-{version}"

    return podman_path, version


def cleanup_podman_files(base_work_dir):
    version = config.project.get_config("prepare.podman.repo.version", print=False)

    dest = base_work_dir / f"podman-{version}"

    if remote_access.exists(dest):
        logging.info(f"Removing {dest} ...")
        prepare.remove_remote_file(base_work_dir, dest, recursive=True)

    dest = base_work_dir / "podman-custom"

    if remote_access.exists(dest):
        logging.info(f"Removing {dest} ...")
        prepare.remove_remote_file(base_work_dir, dest, recursive=True)


def parse_platform(platform_str):
    p = SimpleNamespace()
    p.container_engine = platform_str
    p.platform = config.project.get_config("remote_host.system", print=False)

    if p.container_engine not in ["podman", "docker"]:
        raise ValueError(f"Unsupported container engine: {p.container_engine}. Expected 'podman' or 'docker'.")
    if p.platform not in ["darwin", "windows", "linux"]:
        raise ValueError(f"Unsupported platform: {p.platform}.")

    if p.container_engine == "podman":
        p.prepare_platform = prepare.prepare_podman_platform
        p.cleanup_platform = prepare.cleanup_podman_platform
    elif p.container_engine == "docker":
        p.prepare_platform = prepare.prepare_docker_platform
        p.cleanup_platform = prepare.cleanup_docker_platform

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
    client_file = config.project.get_config("prepare.podman.custom_binary.client_file")
    server_file = config.project.get_config("prepare.podman.custom_binary.server_file")

    podman_path = base_work_dir / "podman-custom" / client_file
    server_podman_path = base_work_dir / "podman-custom" / server_file
    if remote_access.exists(podman_path) and remote_access.exists(server_podman_path):
        logging.info("podman custom already exists, not downloading it.")
        return podman_path

    source = config.project.get_config("prepare.podman.custom_binary.url")
    dest = base_work_dir / "podman-custom" / "podman-custom.zip"

    run.run_toolbox(
        "remote", "download",
        source=source,
        dest=dest,
        zip=True,
    )

    return podman_path


def docker_service(operation):
    logging.info("Stopping Docker service")
    base_work_dir = remote_access.prepare()
    if operation == "stop":
        cmd = "sudo systemctl stop docker.socket"
        remote_access.run_with_ansible_ssh_conf(base_work_dir, cmd)
    cmd = f"sudo systemctl {operation} docker"
    remote_access.run_with_ansible_ssh_conf(base_work_dir, cmd)


def build_podman_from_gh_binary():
    logging.info("Building Podman from GitHub repository")
    base_work_dir = remote_access.prepare()
    path, _ = _get_repo_podman_path(base_work_dir)
    if not remote_access.exists(path):
        logging.fatal("Missing source codes for podman")
        return
    cmd = "make binaries"
    ret = remote_access.run_with_ansible_ssh_conf(
        base_work_dir, cmd, chdir=path, capture_stderr=True, capture_stdout=True
    )
    logging.info(f"stdout:{ret.stdout}")
    logging.info(f"stderr:{ret.stderr}")
