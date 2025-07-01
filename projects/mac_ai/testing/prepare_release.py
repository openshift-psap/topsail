import os
import pathlib
import logging
import tarfile

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

import prepare_llama_cpp, utils, remote_access, podman_machine, brew, podman, prepare_virglrenderer
import llama_cpp, ollama, ramalama

def create_remoting_tarball(base_work_dir):
    package_libs = []
    virglrenderer_lib = prepare_virglrenderer.get_dyld_library_path(base_work_dir, with_lib=True)

    if not remote_access.exists(virglrenderer_lib):
        raise ValueError(f"Cannot publish the remoting libraries, {virglrenderer_lib} does not exist")
    package_libs.append(virglrenderer_lib)

    llama_remoting_backend_build_dir = prepare_llama_cpp.get_remoting_build_dir(base_work_dir)

    ggml_backend_libs = config.project.get_config("prepare.podman.machine.remoting_env.ggml_libs")
    for libname in ggml_backend_libs:
        backend_lib = llama_remoting_backend_build_dir / libname
        if not remote_access.exists(backend_lib):
            raise ValueError(f"Cannot publish the remoting libraries, {backend_lib} does not exist")
        package_libs.append(backend_lib)

    with env.NextArtifactDir("build_remoting_tarball"):
        return build_remoting_tarball(base_work_dir, package_libs)


def add_string_file(dest, content):
    dest.write_text(content)


def add_local_file(location, dest):
    dest.write_text(location.read_text())


def add_remote_file(base_work_dir, location, dest):
    logging.info(f"Preparing {dest.name} ...")
    content_cmd = remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"cat '{location}'",
        capture_stdout=True, decode_stdout=False
    )

    dest.write_bytes(content_cmd.stdout)


def add_remote_git_status(base_work_dir, src_dir, dest):
    git_show_cmd = remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"git -C '{src_dir}' show",
        capture_stdout=True
    )
    git_revparse_cmd = remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"git -C '{src_dir}' rev-parse HEAD",
        capture_stdout=True
    )
    dest.write_text(git_show_cmd.stdout)

    return git_revparse_cmd.stdout.strip()


def get_version_link(repo_url, version, git_rev, github=False, gitlab=False):
    url = f"{repo_url}/-/commit/{git_rev}" if gitlab \
        else f"{repo_url}/commit/{git_rev}"

    if version:
        url += f" (release {version})"

    return url


def build_remoting_tarball(base_work_dir, package_libs):
    llama_cpp_version = config.project.get_config("prepare.llama_cpp.source.repo.version")
    llama_cpp_url = config.project.get_config("prepare.llama_cpp.source.repo.url")

    ramalama_version = config.project.get_config("prepare.ramalama.repo.version")

    virglrenderer_version = config.project.get_config("prepare.virglrenderer.repo.branch")
    virglrenderer_url = config.project.get_config("prepare.virglrenderer.repo.url")

    logging.info(f"Preparing the API remoting data into {env.ARTIFACT_DIR} ...")
    tarball_dir = env.ARTIFACT_DIR / f"llama_cpp-api_remoting-{llama_cpp_version}"
    tarball_dir.mkdir()

    bin_dir = tarball_dir / "bin"
    bin_dir.mkdir()

    src_info_dir = tarball_dir / "src_info"
    src_info_dir.mkdir()

    virglrenderer_src_dir = prepare_virglrenderer.get_build_dir(base_work_dir) / ".." / "src"
    virglrenderer_git_rev = add_remote_git_status(base_work_dir, virglrenderer_src_dir,
                                                  src_info_dir / "virglrenderer.git-commit.txt")

    virglrenderer_version_link = get_version_link(virglrenderer_url, virglrenderer_version, virglrenderer_git_rev, gitlab=True)

    llama_cpp_src_dir = prepare_llama_cpp.get_source_dir(base_work_dir)
    llama_cpp_git_rev = add_remote_git_status(base_work_dir, llama_cpp_src_dir,
                                              src_info_dir / "llama-cpp.git-commit.txt")

    llama_cpp_version_link = get_version_link(llama_cpp_url, llama_cpp_version, llama_cpp_git_rev, github=True)

    for backend_lib in package_libs:
        add_remote_file(base_work_dir, backend_lib, bin_dir / backend_lib.name)

    machine_script_file = pathlib.Path("projects/mac_ai/testing/scripts/podman_start_machine.api_remoting.sh")
    add_local_file(machine_script_file, tarball_dir / machine_script_file.name)

    krunkit_script_file = pathlib.Path("projects/mac_ai/testing/scripts/update_krunkit.sh")
    add_local_file(krunkit_script_file, tarball_dir / krunkit_script_file.name)

    registry_path = config.project.get_config("prepare.ramalama.build_image.registry_path")
    image_name = config.project.get_config("prepare.ramalama.build_image.name")
    ramalama_image = f"{registry_path}/{image_name}:{llama_cpp_version}"

    import prepare_mac_ai
    _, ramalama_src_dir, _ = ramalama._get_binary_path(base_work_dir, prepare_mac_ai.RAMALAMA_REMOTING_PLATFORM)

    ramalama_git_revparse = add_remote_git_status(base_work_dir, ramalama_src_dir,
                                                  src_info_dir / "ramalama.git-commit.txt")

    ramalama_repo_url = config.project.get_config("prepare.ramalama.repo.url")

    ramalama_version_link = get_version_link(ramalama_repo_url, ramalama_version, ramalama_git_revparse, github=True)

    add_string_file(src_info_dir / "ramalama.image-info.txt", ramalama_image + "\n")

    entitlement_dir = tarball_dir / "entitlement"
    entitlement_dir.mkdir()

    entitlement_file = pathlib.Path("projects/mac_ai/testing/scripts/krunkit.entitlements")
    add_local_file(entitlement_file, entitlement_dir / entitlement_file.name)

    # ---

    ci_build_link = None
    ci_perf_link = None
    if os.environ.get("OPENSHIFT_CI") == "true":
        ci_link = "/".join([
            "https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/test-platform-results/pr-logs/pull",
            os.environ["REPO_OWNER"] + "_" + os.environ["REPO_NAME"],
            os.environ["PULL_NUMBER"],
            os.environ["JOB_NAME"],
            os.environ["BUILD_ID"],
            "artifacts",
            os.environ["JOB_NAME_SAFE"],
        ])
        ci_build_link = ci_link + "/" + os.environ["TOPSAIL_OPENSHIFT_CI_STEP_DIR"]
        ci_perf_link = ci_link + "/005-test/artifacts/test-artifacts/reports_index.html"

    tarball_file = env.ARTIFACT_DIR / f"llama_cpp-api_remoting-{llama_cpp_version}.tar"

    tarball_path = pathlib.Path(env.ARTIFACT_DIR.name) / tarball_file.name
    add_string_file(tarball_dir / "README.md", f"""\
llama.cpp API remoting GPU acceleration for MacOS
=================================================

* Make sure that the following dependencies are installed

```
brew tap slp/krunkit
brew install krunkit

brew install podman ramalama
```

* Make sure that a libkrun Podman machine exists
```
export CONTAINERS_MACHINE_PROVIDER=libkrun

podman machine ls

# if you don't have a libkrun machine:
podman machine init
```

* from inside the tarball directory, run this command once to create a copy of krunkit/libkrun that will be allowed to run our virglrenderer/llama.cpp libraries
```
bash ./{krunkit_script_file.name}
```

* run this command to restart the libkrun podman machine with our libraries
```
bash ./{machine_script_file}
```

* run ramalama with our custom image.
```
export CONTAINERS_MACHINE_PROVIDER=libkrun
ramalama --image {ramalama_image} run llama3.2
```

Sources
-------
virglrenderer source: {virglrenderer_version_link}
llama.cpp source    : {llama_cpp_version_link}
ramalama source     : {ramalama_version_link}

Ramalama image
--------------
{ramalama_image}

CI build
--------
* tarball: {ci_build_link / tarball_path if ci_build_link else '(Not running in a CI environment)'}
* build logs: {ci_build_link or '(Not running in a CI environment)'}

CI performance test
--------
{ci_perf_link or '(Not running in a CI environment)'}
""")

    with tarfile.open(tarball_file, "w") as tar:
        tar.add(tarball_dir, tarball_dir.relative_to(env.ARTIFACT_DIR))

    logging.info(f"Saved {tarball_file} !")
