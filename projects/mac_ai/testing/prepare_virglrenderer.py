import os
import pathlib
import logging

from projects.core.library import env, config, run, configure_logging, export
from projects.remote.lib import remote_access


def get_build_dir(base_work_dir):
    version = config.project.get_config("prepare.virglrenderer.repo.branch")

    return base_work_dir / "virglrenderer" / version / "build"


def get_dyld_library_path(base_work_dir, with_lib=False):
    path = get_build_dir(base_work_dir) / "src"
    if with_lib:
        path /= "libvirglrenderer.1.dylib"

    return path


def get_virgl_render_server_path(base_work_dir):
    return get_build_dir(base_work_dir) / "server/virgl_render_server"


def prepare(base_work_dir):
    if not config.project.get_config("prepare.virglrenderer.enabled"):
        logging.info("Custom virglrenderer not enabled, not preparing it.")
        return

    # don't check if already exists, always build it

    repo_url = config.project.get_config("prepare.virglrenderer.repo.url")
    build_flags = config.project.get_config("prepare.virglrenderer.build.flags")

    if config.project.get_config("prepare.virglrenderer.debug.enabled"):
        build_flags += " " + config.project.get_config("prepare.virglrenderer.debug.flags")

    version = config.project.get_config("prepare.virglrenderer.repo.branch")
    refspec = None
    if version.startswith("pr-"):
        pr_number = version.removeprefix("pr-")
        refspec = f"refs/merge-requests/{pr_number}/head"
        version = None

    build_dir = get_build_dir(base_work_dir)
    src_dir = build_dir.parent / "src"

    run.run_toolbox(
        "remote", "clone",
        repo_url=repo_url,
        dest=src_dir,
        version=version,
        refspec=refspec,
        artifact_dir_suffix="__virglrenderer",
        force=True,
    )

    run.run_toolbox(
        "mac_ai", "remote_build_virglrenderer",
        source_dir=src_dir,
        build_dir=build_dir,
        build_flags=build_flags,
    )


def configure(base_work_dir, use_custom):
    if config.project.get_config("remote_host.system") != "darwin":
        return

    BREW_CUSTOM_DIR = pathlib.Path("/opt/homebrew/Cellar/virglrenderer/0.10.4d/lib/custom")
    BREW_CUSTOM_LIB = BREW_CUSTOM_DIR / "libvirglrenderer.1.dylib.current"

    BREW_LIBRARY_PATH = BREW_CUSTOM_DIR / "libvirglrenderer.1.dylib.brew"

    if use_custom:
        library_path = get_dyld_library_path(base_work_dir) / "libvirglrenderer.1.dylib"

        if not remote_access.exists(library_path):
            # restore the default before aborting
            remote_access.symlink_to(BREW_CUSTOM_LIB, BREW_CUSTOM_LIB)
            raise RuntimeError(f"Library at '{library_path}' does not exists ...")
    else:
        library_path = BREW_LIBRARY_PATH

    remote_access.symlink_to(BREW_CUSTOM_LIB, library_path)


def has_custom_virglrenderer(base_work_dir):
    virglrenderer_path = remote_access.run_with_ansible_ssh_conf(base_work_dir, "lsof -c krunkit | grep virglrenderer", check=False, capture_stdout=True).stdout.strip()

    return str(get_dyld_library_path(base_work_dir)) in virglrenderer_path


def cleanup(base_work_dir):
    configure(base_work_dir, use_custom=False)

    dest = base_work_dir / f"virglrenderer"

    if not remote_access.exists(dest):
        logging.info(f"{dest} does not exists, nothing to remove.")
        return

    logging.info(f"Removing {dest} ...")
    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -rf {dest}")
