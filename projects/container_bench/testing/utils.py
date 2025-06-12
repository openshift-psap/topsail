import tempfile
import os
from projects.core.library import config
from projects.core.library import run
import remote_access
import logging
from types import SimpleNamespace
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

    run.run_toolbox(
        "remote", "download",
        source=source,
        dest=gvisor_path,
        executable=True,
    )


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

    if not remote_access.exists(dest):
        logging.info(f"{dest} does not exists, nothing to remove.")
        return

    logging.info(f"Removing {dest} ...")
    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -rf {dest}")


def parse_benchmark(benchmark):
    benchmark = SimpleNamespace()
    benchamrk_parts = benchmark.split("/")
    if len(benchamrk_parts) != 3:
        raise ValueError(
            f"Invalid benchmark format: {benchmark}. Expected format is 'container_engine/platform/benchmark'.")
    benchmark.container_engine = benchamrk_parts[0]
    benchmark.platform = benchamrk_parts[1]
    benchmark.benchmark = benchamrk_parts[2]

    if benchmark.container_engine not in ["podman", "docker"]:
        raise ValueError(f"Unsupported container engine: {benchmark.container_engine}. Expected 'podman' or 'docker'.")
    if benchmark.platform not in ["darwin"]:  # TODO: Implement "linux", "windows"
        raise ValueError(f"Unsupported platform: {benchmark.platform}.")

    return benchmark
