import os
import pathlib
import logging

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

import remote_access
import podman as podman_mod
import utils

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent

def resolve_latest_version():
    def resolve(prefix):
        version = config.project.get_config(f"{prefix}.repo.version", print=False)

        if version != "latest":
            return

        repo_url = config.project.get_config(f"{prefix}.repo.url")
        version = utils.get_latest_release(repo_url)
        config.project.set_config(f"{prefix}.repo.version", version)

    resolve("prepare.llama_cpp.source")
    resolve("prepare.llama_cpp.release")

def prepare_test(base_work_dir, platform):
    resolve_latest_version()

    if not platform.needs_podman: return

    local_image_name = get_local_image_name(base_work_dir, platform)
    config.project.set_config("prepare.podman.container.image", local_image_name)
    build_from = config.project.get_config("prepare.llama_cpp.source.podman.build_from")
    command = config.project.get_config(f"prepare.llama_cpp.source.podman.{build_from}.command")
    config.project.set_config("prepare.llama_cpp.source.podman.command", command)


def get_local_image_name(base_work_dir, platform):
    build_from = config.project.get_config("prepare.llama_cpp.source.podman.build_from")

    if build_from == "desktop_playground":
        return __get_local_image_name_from_desktop_playground(base_work_dir, platform)

    if build_from == "local_container_file":
        return __get_local_image_name_from_local_container_file(platform)

    raise ValueError(f"{build_from} not in {', '.join(FROM.keys())}")


def __get_local_image_name_from_local_container_file(platform):
    container_file = TESTING_THIS_DIR / config.project.get_config("prepare.llama_cpp.source.podman.local_container_file.path")

    if not platform.inference_server_flavor:
        raise ValueError(f"Platform {platform} doesn't have a flavor :/")

    inference_server_flavor = platform.inference_server_flavor
    version = config.project.get_config("prepare.llama_cpp.source.repo.version")
    tag = f"{version}-{inference_server_flavor}"
    return f"localhost/llama_cpp:{tag}"


def prepare_for_podman(base_work_dir, platform):
    FROM = dict(
        local_container_file=prepare_podman_image_from_local_container_file,
    )
    build_from = config.project.get_config("prepare.llama_cpp.source.podman.build_from")
    if build_from not in FROM:
        raise ValueError(f"{build_from} not in {', '.join(FROM.keys())}")

    return FROM[build_from](base_work_dir, platform)


def prepare_podman_image_from_local_container_file(base_work_dir, platform):
    local_image_name = __get_local_image_name_from_local_container_file(platform)
    container_file = TESTING_THIS_DIR / config.project.get_config("prepare.llama_cpp.source.podman.local_container_file.path")
    build_args = config.project.get_config("prepare.llama_cpp.source.podman.local_container_file.build_args")

    if podman_mod.has_image(base_work_dir, local_image_name):
        logging.info(f"Image {local_image_name} already exists, not rebuilding it.")
        return

    if not platform.inference_server_flavor:
        raise ValueError(f"Platform {platform} doesn't have a flavor :/")

    inference_server_flavor = platform.inference_server_flavor
    flavors = config.project.get_config("prepare.llama_cpp.source.podman.local_container_file.flavors")
    flavor_cmake_flags = flavors.get(inference_server_flavor)
    if flavor_cmake_flags is None:
        raise ValueError(f"Invalid platform flavor: {inference_server_flavor}. "
                         f"Expected one of {', '.join(flavors)}")


    cmake_flags = build_args["LLAMA_CPP_CMAKE_FLAGS"] or ""
    cmake_flags += " " + flavor_cmake_flags

    cmake_parallel = config.project.get_config("prepare.llama_cpp.source.cmake.parallel")
    cmake_build_flags = f"--parallel {cmake_parallel}"

    build_args["BUILD_FLAVOR"] = inference_server_flavor
    build_args["LLAMA_CPP_CMAKE_FLAGS"] = cmake_flags
    build_args["LLAMA_CPP_CMAKE_BUILD_FLAGS"] = cmake_build_flags

    build_args["LLAMA_CPP_REPO"] = config.project.resolve_reference(build_args["LLAMA_CPP_REPO"])
    version = build_args["LLAMA_CPP_VERSION"] = config.project.resolve_reference(build_args["LLAMA_CPP_VERSION"])

    if version.startswith("pr-"):
        pr_number = version.removeprefix("pr-")
        build_args["LLAMA_CPP_VERSION"] = f"refs/pull/{pr_number}/head"

    artifact_dir_suffix = "_" + "_".join([pathlib.Path(container_file).name, inference_server_flavor])

    run.run_toolbox(
        "remote", "build_image",
        podman_cmd=podman_mod.get_podman_binary(base_work_dir),
        base_directory=None,
        prepare_script=None,
        container_file=container_file,
        container_file_is_local=True,
        image=local_image_name,
        build_args=build_args,
        artifact_dir_suffix=artifact_dir_suffix,
    )


def prepare_from_release(base_work_dir, platform):
    error_msg = utils.check_expected_platform(platform, system="macos", inference_server_name="llama_cpp", inference_server_flavor="upstream_bin")
    if error_msg:
        raise ValueError(f"prepare_llama_cpp.prepare_from_release: unexpected platform: {error_msg} :/")

    tarball = config.project.get_config("prepare.llama_cpp.release.tarball")
    if not tarball:
        raise ValueError("llama_cpp on MacOS/Darwin should be a tarball :/")

    llama_cpp_path, dest, platform_file, version = _get_binary_path(base_work_dir, platform, for_release=True)

    source = "/".join([
        config.project.get_config("prepare.llama_cpp.release.repo.url"),
        "releases/download",
        version,
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
    version = config.project.get_config("prepare.llama_cpp.source.repo.version")

    dirname = "llama.cpp-"
    if version.startswith("pr-"):
        dirname += version
    else:
        dirname += f"tag-{version}"

    dest = base_work_dir / "llama_cpp" / dirname

    if not remote_access.exists(dest):
        repo_url = config.project.get_config("prepare.llama_cpp.source.repo.url")

        kwargs = dict(
            repo_url=repo_url,
            dest=dest,
        )

        if version.startswith("pr-"):
            pr_number = version.removeprefix("pr-")
            kwargs["refspec"] = f"refs/pull/{pr_number}/head"
        else:
            kwargs["version"] = version

        run.run_toolbox(
            "remote", "clone",
            **kwargs,
            artifact_dir_suffix="_llama_cpp",
        )

        # for the Kompute build
        cmd = f"sed -i.bu s/-Werror//g {dest}/ggml/src/ggml-kompute/kompute/CMakeLists.txt"
        remote_access.run_with_ansible_ssh_conf(base_work_dir, cmd)

    src_dir = dest
    cmake_parallel = config.project.get_config("prepare.llama_cpp.source.cmake.parallel")

    if not platform.inference_server_flavor:
        raise ValueError(f"Platform {platform} doesn't have a flavor :/")

    inference_server_flavor = platform.inference_server_flavor
    flavors_cmake_flags = config.project.get_config("prepare.llama_cpp.source.cmake.flavors")
    if inference_server_flavor not in flavors_cmake_flags:
        msg = f"Invalid llama-cpp compile flavor: {inference_server_flavor}. Expected one of {', '.join(flavors_cmake_flags.keys())}."
        logging.fatal(msg)
        raise ValueError(msg)

    build_dir = dest.parent / f"build-{platform.name.replace('/', '-')}-{version}"

    llama_cpp_server_path = build_dir / "bin" / "llama-server"
    if remote_access.exists(llama_cpp_server_path):
        logging.info(f"{llama_cpp_server_path} already exists. Not recompiling it.")
        return llama_cpp_server_path

    cmake_flags = config.project.get_config("prepare.llama_cpp.source.cmake.common")
    cmake_flags += " " + flavors_cmake_flags[inference_server_flavor]

    if config.project.get_config("prepare.llama_cpp.source.cmake.openmp.enabled"):
        cmake_flags += " " + config.project.get_config("prepare.llama_cpp.source.cmake.openmp.flags")

    with env.NextArtifactDir(f"build_llama_cpp_{inference_server_flavor}"):
        prepare_cmd = f"cmake -B {build_dir} {cmake_flags} 2>&1 | tee {build_dir}/build.prepare.log"
        build_cmd = f"cmake --build {build_dir} --config Release --parallel {cmake_parallel} 2>&1 | tee {build_dir}/build.compile.log"

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
            raise RuntimeError(f"Failed to prepare llama-cpp/{inference_server_flavor}. See {env.ARTIFACT_DIR}/prepare.log")

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
            raise RuntimeError(f"Failed to build llama-cpp/{inference_server_flavor}. See {env.ARTIFACT_DIR}/build.log")

    return llama_cpp_server_path


def prepare_for_macos(base_work_dir, platform):
    error_msg = utils.check_expected_platform(platform, system="macos", inference_server_name="llama_cpp")
    if error_msg:
        raise ValueError(f"prepare_for_macos: unexpected platform: {error_msg} :/")

    if not platform.inference_server_flavor:
        raise ValueError(f"Platform {platform} doesn't have a flavor :/")

    if platform.inference_server_flavor == "upstream_bin":
        return prepare_from_release(base_work_dir, platform)
    else:
        return prepare_from_source(base_work_dir, platform)


def prepare_binary(base_work_dir, platform):
    resolve_latest_version()

    if platform.system == "macos":
        return prepare_for_macos(base_work_dir, platform)

    if platform.system == "podman":
        return prepare_for_podman(base_work_dir, platform)

    raise ValueError(f"Invalid platform.system to prepare: {platform.system}. Expected one of [macos, podman].")


def _get_binary_path(base_work_dir, platform, for_release=False):
    if platform.needs_podman:
        podman_prefix = podman_mod.get_exec_command_prefix()
        container_command = config.project.get_config("prepare.llama_cpp.source.podman.command")
        command = f"{podman_prefix} {container_command}"

        return command, None, None, None

    version = config.project.get_config(f"prepare.llama_cpp.{'release' if for_release else 'source'}.repo.version", print=False)

    if not utils.check_expected_platform(platform, system="macos", inference_server_name="llama_cpp", inference_server_flavor="upstream_bin"):
        file_name = config.project.get_config("prepare.llama_cpp.release.file")

        dest = base_work_dir / "llama_cpp" / f"release-{platform.system}-{version}" / file_name
        llama_cpp_path = dest.parent / "build" / "bin" / "llama-server"

        return llama_cpp_path, dest, file_name, version
    elif platform.system == "macos":
        llama_cpp_path = base_work_dir / "llama_cpp" / f"build-{platform.name.replace('/', '-')}-{version}" / "bin" / "llama-server"
        return llama_cpp_path, None, None, version
    else:
        pass

    raise ValueError(f"Invalid platform: {platform}. Expected macos/llama_cpp/upstream_bin, podman/llama_cpp/*, macos/llama_cpp/*")


def get_binary_path(base_work_dir, platform):
    for_release = ""
    llama_cpp_path, _, _, _ = _get_binary_path(base_work_dir, platform,
                                               for_release=(platform.inference_server_flavor == "upstream_bin"))
    return llama_cpp_path


def cleanup_files(base_work_dir):
    dest = base_work_dir / "llama_cpp"

    if not remote_access.exists(dest):
        logging.info(f"{dest} does not exists, nothing to remove.")
        return

    logging.info(f"Removing {dest} ...")
    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -r {dest}")


def cleanup_image(base_work_dir):
    platforms_to_build_str = config.project.get_config("prepare.platforms.to_build")
    if not platforms_to_build_str:
        platforms_to_build_str = config.project.get_config("test.platform")

    if not isinstance(platforms_to_build_str, list):
        platforms_to_build_str = [platforms_to_build_str]

    for platform_str in platforms_to_build_str:
        platform = utils.parse_platform(platform_str)
        if not platform.needs_podman: continue

        prepare_test(base_work_dir, platform)

        local_image_name = __get_local_image_name_from_local_container_file(platform)

        if not podman_mod.has_image(base_work_dir, local_image_name):
            logging.info(f"Image {local_image_name} does not exist, nothing to remove.")
            continue

        podman_mod.rm_image(base_work_dir, local_image_name)
