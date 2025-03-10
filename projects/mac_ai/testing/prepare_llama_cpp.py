import os
import pathlib
import logging

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

import remote_access
import podman as podman_mod

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent

def prepare_test(base_work_dir, platform):
    if "podman" not in platform: return

    local_image_name = get_local_image_name(base_work_dir, platform)
    config.project.set_config("prepare.podman.container.image", local_image_name)
    build_from = config.project.get_config("prepare.llama_cpp.repo.podman.build_from")
    command = config.project.get_config(f"prepare.llama_cpp.repo.podman.{build_from}.command")
    config.project.set_config("prepare.llama_cpp.repo.podman.command", command)


def get_local_image_name(base_work_dir, platform):
    build_from = config.project.get_config("prepare.llama_cpp.repo.podman.build_from")

    if build_from == "desktop_playground":
        return __get_local_image_name_from_desktop_playground(base_work_dir, platform)

    if build_from == "local_container_file":
        return __get_local_image_name_from_local_container_file(platform)

    raise ValueError(f"{build_from} not in {', '.join(FROM.keys())}")


def __get_local_image_name_from_local_container_file(platform):
    container_file = TESTING_THIS_DIR / config.project.get_config("prepare.llama_cpp.repo.podman.local_container_file.path")

    flavor = platform.split("/")[-1]
    version = config.project.get_config("prepare.llama_cpp.repo.podman.local_container_file.build_args.LLAMA_CPP_VERSION")
    tag = f"{version}-{flavor}"
    return f"localhost/llama_cpp:{tag}"


def __get_local_image_name_from_desktop_playground(base_work_dir, repo_cfg, only_dest=False):
    repo_cfg = config.project.get_config("prepare.llama_cpp.repo.podman.desktop_playground")
    repo_url = repo_cfg["url"]
    dest = base_work_dir / pathlib.Path(repo_url).name

    if only_dest:
        return dest

    image = repo_cfg["image"]
    tag = repo_cfg["tag"]

    if not tag:
        ret = remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            f"git -C {dest} rev-parse --short HEAD",
            capture_stdout=True,
        )
        tag = ret.stdout.strip()
        config.project.set_config("prepare.llama_cpp.repo.podman.tag", tag)

    return f"localhost/{image}:{tag}", dest


def prepare_for_podman(base_work_dir, platform):
    FROM = dict(
        desktop_playground=prepare_podman_image_from_desktop_playground,
        local_container_file=prepare_podman_image_from_local_container_file,
    )
    build_from = config.project.get_config("prepare.llama_cpp.repo.podman.build_from")
    if build_from not in FROM:
        raise ValueError(f"{build_from} not in {', '.join(FROM.keys())}")

    return FROM[build_from](base_work_dir, platform)


def prepare_podman_image_from_local_container_file(base_work_dir, platform):
    local_image_name = __get_local_image_name_from_local_container_file(platform)
    container_file = TESTING_THIS_DIR / config.project.get_config("prepare.llama_cpp.repo.podman.local_container_file.path")
    build_args = config.project.get_config("prepare.llama_cpp.repo.podman.local_container_file.build_args")

    if podman_mod.has_image(base_work_dir, local_image_name):
        logging.info(f"Image {local_image_name} already exists, not rebuilding it.")
        return

    flavor = platform.split("/")[-1]
    flavors = config.project.get_config("prepare.llama_cpp.repo.podman.local_container_file.flavors")
    cmake_flags = flavors.get(flavor)
    if cmake_flags is None:
        raise ValueError(f"Invalid image flavor: {platform}. Expected one of {', '.join(flavors)}")

    build_args["LLAMA_CPP_CMAKE_FLAGS"] = cmake_flags

    artifact_dir_suffix = "_" + "_".join([pathlib.Path(container_file).name, flavor])

    run.run_toolbox(
        "remote", "build_image",
        podman_cmd=podman_mod.get_podman_binary(),
        base_directory=None,
        prepare_script=None,
        container_file=container_file,
        container_file_is_local=True,
        image=local_image_name,
        build_args=build_args,
        artifact_dir_suffix=artifact_dir_suffix,
    )


def prepare_podman_image_from_desktop_playground(base_work_dir, platform):
    repo_cfg = config.project.get_config("prepare.llama_cpp.repo.podman.desktop_playground")
    repo_url = repo_cfg["url"]

    # cannot compute the image tag if the repo isn't cloned ...
    dest = __get_local_image_name_from_desktop_playground(base_work_dir, repo_cfg, only_dest=True)

    ref = repo_cfg["ref"]
    run.run_toolbox(
        "remote", "clone",
        repo_url=repo_url, dest=dest, version=ref,
    )

    root_directory = repo_cfg["root_directory"]
    container_file = repo_cfg["container_file"]
    image = repo_cfg["image"]
    tag = repo_cfg["tag"]

    if config.project.get_config("prepare.podman.machine.enabled"):
        podman_machine.configure_and_start(base_work_dir, force_restart=False)

    local_image_name, _ = __get_local_image_name(base_work_dir, platform)

    run.run_toolbox(
        "remote", "build_image",
        podman_cmd=podman_mod.get_podman_binary(),
        base_directory=dest / root_directory,
        prepare_script=repo_cfg["prepare_script"],
        container_file=container_file,
        image=local_image_name,
    )

    return local_image_name


def prepare_from_binary(base_work_dir, platform="darwin"):
    if not platform == "darwin/upstream":
        raise ValueError(f"Expected the platform to be 'darwin/upstream', got '{platform}'")

    tarball = config.project.get_config(f"prepare.llama_cpp.repo.darwin.upstream.tarball")
    if not tarball:
        raise ValueError("llama_cpp on darwin should be a tarball :/")

    llama_cpp_path, dest, platform_file = _get_binary_path(base_work_dir, platform)

    source = "/".join([
        config.project.get_config("prepare.llama_cpp.repo.url"),
        "releases/download",
        config.project.get_config(f"prepare.llama_cpp.repo.version"),
        platform_file,
    ])

    if remote_access.exists(llama_cpp_path):
        logging.info(f"llama_cpp {platform} already exists, not downloading it.")
        return llama_cpp_path

    run.run_toolbox(
        "remote", "download",
        source=source,
        dest=dest,
        tarball=tarball,
    )

    return llama_cpp_path


def prepare_from_source(base_work_dir, platform):
    version = config.project.get_config(f"prepare.llama_cpp.repo.version")

    file_name = f"{version}.tar.gz"

    dest = base_work_dir / "llama_cpp" / f"llama.cpp-tags-{version}"

    if not remote_access.exists(dest):
        repo_url = config.project.get_config(f"prepare.llama_cpp.repo.url")

        run.run_toolbox(
            "remote", "clone",
            repo_url=repo_url, dest=dest, version=version,
            artifact_dir_suffix="_llama_cpp",
        )

        # for the Kompute build
        cmd = f"sed -i.bu s/-Werror//g llama_cpp/llama.cpp-tags-{version}/ggml/src/ggml-kompute/kompute/CMakeLists.txt"
        remote_access.run_with_ansible_ssh_conf(base_work_dir, cmd)

    src_dir = dest.parent / f"llama.cpp-tags-{version}"
    cmake_parallel = config.project.get_config("prepare.llama_cpp.repo.source.cmake.parallel")

    flavor = platform.rpartition("/")[-1]
    flavors_cmake_flags = config.project.get_config("prepare.llama_cpp.repo.source.cmake.flavors")
    if flavor not in flavors_cmake_flags:
        msg = f"Invalid llama-cpp compile flavor: {flavor}. Expected one of {', '.join(flavors_cmake_flags.keys())}."
        logging.fatal(msg)
        raise ValueError(msg)

    build_dir = dest.parent / f"build-{platform.replace('/', '-')}-{version}"

    llama_cpp_server_path = build_dir / "bin" / "llama-server"
    if remote_access.exists(llama_cpp_server_path):
        logging.info(f"{llama_cpp_server_path} already exists. Not recompiling it.")
        return llama_cpp_server_path

    cmake_flags = config.project.get_config("prepare.llama_cpp.repo.source.cmake.common")
    cmake_flags += " " + flavors_cmake_flags[flavor]

    with env.NextArtifactDir(f"build_llama_cpp_{flavor}"):
        prepare_cmd = f"cmake -B {build_dir} {cmake_flags} | tee {build_dir}/build.prepare.log"
        build_cmd = f"cmake --build {build_dir} --config Release --parallel {cmake_parallel} | tee {build_dir}/build.compile.log"

        ret = remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            f"mkdir -p '{build_dir}' && echo 'Build flags: {cmake_flags}' > {build_dir}/build.flags.log",
            chdir=src_dir,
            capture_stdout=True,
        )

        with open(env.ARTIFACT_DIR / "prepare.cmd", "a") as f:
            print(prepare_cmd, file=f)

        with open(env.ARTIFACT_DIR / "build.cmd", "a") as f:
            print(build_cmd, file=f)

        ret = remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            prepare_cmd,
            chdir=src_dir,
            capture_stdout=True,
            check=False,
        )

        with open(env.ARTIFACT_DIR / "prepare.log", "w") as f:
            print(f"# prepare command: {prepare_cmd}", file=f)
            print(ret.stdout, file=f)

        if ret.returncode != 0:
            raise RuntimeError(f"Failed to prepare llama-cpp/{flavor}. See {env.ARTIFACT_DIR}/prepare.log")

        ret = remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            build_cmd,
            chdir=src_dir,
            capture_stdout=True,
            check=False,
        )

        with open(env.ARTIFACT_DIR / "build.log", "w") as f:
            print(f"# build command: {build_cmd}", file=f)
            print(ret.stdout, file=f)

        if ret.returncode != 0:
            raise RuntimeError(f"Failed to build llama-cpp/{flavor}. See {env.ARTIFACT_DIR}/build.log")

    return llama_cpp_server_path


def prepare_for_darwin(base_work_dir, platform):
    build_from = platform.rpartition("/")[-1]

    if build_from == "upstream":
        return prepare_from_binary(base_work_dir, platform)
    else:
        return prepare_from_source(base_work_dir, platform)


def prepare_binary(base_work_dir, platform):
    if platform.startswith("darwin"):
        return prepare_for_darwin(base_work_dir, platform)

    if platform.startswith("podman"):
        return prepare_for_podman(base_work_dir, platform)

    raise ValueError(f"Invalid platform to prepare: {platform}. Expected one of darwin/*, podman/*.")


def _get_binary_path(base_work_dir, platform):
    if platform.startswith("podman"):
        podman_prefix = podman_mod.get_exec_command_prefix()
        container_command = config.project.get_config(f"prepare.llama_cpp.repo.podman.command")
        command = f"{podman_prefix} {container_command}"

        return command, None, None

    version = config.project.get_config(f"prepare.llama_cpp.repo.version")
    arch = config.project.get_config("remote_host.arch")

    if platform == "darwin/upstream":
        file_name = config.project.get_config(f"prepare.llama_cpp.repo.darwin.upstream.file")
        dest = base_work_dir / "llama_cpp" / f"release-{platform}-{version}" / file_name
        llama_cpp_path = dest.parent / "build" / "bin" / "llama-server"

        return llama_cpp_path, dest, file_name
    elif platform.startswith("darwin/"):
        llama_cpp_path = base_work_dir / "llama_cpp" / f"build-{platform.replace('/', '-')}-{version}" / "bin" / "llama-server"
        return llama_cpp_path, None, None
    else:
        pass

    raise ValueError(f"Invalid platform: {platform}. Expected darwin/native, podman/*, darwin/*")


def get_binary_path(base_work_dir, platform):
    llama_cpp_path, _, _ = _get_binary_path(base_work_dir, platform)
    return llama_cpp_path


def cleanup_files(base_work_dir):
    dest = base_work_dir / "llama_cpp"

    if not remote_access.exists(dest):
        logging.info(f"{dest} does not exists, nothing to remove.")
        return

    logging.info(f"Removing {dest} ...")
    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -r {dest}")


def cleanup_image(base_work_dir):
    for platform in config.project.get_config("prepare.platforms"):
        if not platform.startswith("podman"): continue

        prepare_test(base_work_dir, platform)

        local_image_name = __get_local_image_name_from_local_container_file(platform)

        if not podman_mod.has_image(base_work_dir, local_image_name):
            logging.info(f"Image {local_image_name} does not exist, nothing to remove.")
            continue

        podman_mod.rm_image(base_work_dir, local_image_name)
