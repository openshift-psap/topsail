import os
import pathlib
import logging
import secrets
import string
import yaml

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize
from projects.remote.lib import remote_access

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
CRC_MAC_AI_SECRET_PATH = pathlib.Path(os.environ.get("CRC_MAC_AI_SECRET_PATH", "/env/CRC_MAC_AI_SECRET_PATH/not_set"))


def cleanup():
    base_work_dir = remote_access.prepare()
    crc_dir = base_work_dir / "crc"

    if config.project.get_config("cleanup.crc_dir.all"):
        remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -rf '{crc_dir}'")
        return

    to_cleanup = config.project.get_config("cleanup.crc_dir")
    # List contents of crc_dir and remove files/directories whose cleanup isn't disabled
    contents_raw = remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"ls -1 '{crc_dir}' 2>/dev/null",
        check=False,
        capture_stdout=True
    ).stdout
    contents_result = [ln.strip() for ln in contents_raw.splitlines() if ln.strip()]

    for item in contents_result:
        item_name = item.strip()
        if not item_name: continue

        item_path = crc_dir / item_path

        should_cleanup = to_cleanup.get(item_name, True)
        if not should_cleanup:
            logging.info(f"Skipping cleanup of {item_path}")
            continue

        logging.info(f"Cleaning up {item_path}")
        remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -rf '{item_path}'")

    if not contents_result:
        logging.info(f"No contents found in {crc_dir} or directory doesn't exist")


    return 0


def get_bundle_file_path(base_work_dir):
    bundles_dir = base_work_dir / "crc/bundles"
    cfg = config.project.get_config("prepare.crc.bundle")
    return bundles_dir / f"crc_{cfg['hypervisor']}_{cfg['version']}_{cfg['arch']}.crcbundle"


def get_bundle_dir(base_work_dir):
    bundle_file_path = get_bundle_file_path(base_work_dir)
    return bundle_file_path.parent / bundle_file_path.stem


def kill_vfkit(base_work_dir):
    try:
        vfkit_pid = remote_access.read("/tmp/vfkit.pid").strip()
    except Exception:
        vfkit_pid = None

    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"kill -9 {int(vfkit_pid)}", # will raise an exception if pid isn't an int
        check=False,
    )

def prepare_crc_bundle(base_work_dir):
    bundle_file_path = get_bundle_file_path(base_work_dir)
    remote_access.mkdir(bundle_file_path.parent)

    bundle_cfg = config.project.get_config("prepare.crc.bundle")
    base_url = config.project.get_config("prepare.crc.bundle.source.base_url")
    source = f"{base_url}/{bundle_cfg['flavor']}/{bundle_cfg['version']}/{bundle_file_path.name}"

    if remote_access.exists(bundle_file_path):
        logging.info(f"Bundle already exists at {bundle_file_path}, not downloading it again.")
    else:
        run.run_toolbox(
            "remote", "download",
            source=source,
            dest=bundle_file_path,
            artifact_dir_suffix="__crcbundle",
            tarball=True,
        )

    machine_dir = base_work_dir / "crc" / "machine"
    remote_access.mkdir(machine_dir)

    kill_vfkit(base_work_dir) # to avoid the disk being used while copying it ...

    bundle_dir = get_bundle_dir(base_work_dir)
    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"rm -f '{machine_dir}/id_ecdsa_crc'" # it's 600, so `cp` doesn't work ...
    )

    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"ssh-keygen -y -f '{bundle_dir}'/id_ecdsa_crc > '{bundle_dir}'/id_ecdsa_crc.pub"
    )

    logging.info("Copying the VM disk to the machine directory ...")
    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"cp '{bundle_dir}'/{{crc.img,id_ecdsa_crc,id_ecdsa_crc.pub,kubeconfig}} '{machine_dir}/'"
    )

    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"sha256sum '{bundle_dir}'/crc.img '{machine_dir}/crc.img'"
    )


def get_crc_ssh_private_key(base_work_dir):
    return base_work_dir / "crc" / "machine" / "id_ecdsa_crc"


def get_crc_binary_path(base_work_dir):
    crc_dir = base_work_dir / "crc" / "crc"
    crc_binary_path = crc_dir / "usr/local/crc/crc"
    vfkit_binary_path = crc_dir / "usr/local/crc/vfkit"

    return crc_dir, crc_binary_path, vfkit_binary_path

def get_oc_binary_path(base_work_dir):
    bundle_dir = get_bundle_dir(base_work_dir)

    return bundle_dir / "oc"

def prepare_crc_binary(base_work_dir):
    base_url = config.project.get_config("prepare.crc.binary.base_url")
    filename = config.project.get_config("prepare.crc.binary.filename")
    source = f"{base_url}/{filename}"

    crc_dir, crc_binary_path, vfkit_binary_path = get_crc_binary_path(base_work_dir)

    if remote_access.exists(crc_binary_path):
        logging.info(f"CRC binary already exists at {crc_binary_path}, not downloading it again.")
    else:
        pkg_file_dest = crc_dir / filename
        run.run_toolbox(
            "remote", "download",
            source=source,
            dest=pkg_file_dest,
            artifact_dir_suffix="__crcbundle",
        )

        remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            f"xar -xf '{filename}' && cat crc.pkg/Payload | gunzip -dc | cpio -i",
            chdir=crc_dir)

        if not remote_access.exists(crc_binary_path):
            raise RuntimeError(f"CRC not properly extracted at {crc_binary_path}")

    if not remote_access.exists(vfkit_binary_path):
        raise RuntimeError(f"VFKIT not found at {vfkit_binary_path} (but CRC was found ...)")


def generate_random_password(password_length=64):
    # Define the set of Base64 characters
    # A-Z, a-z, 0-9, plus '+' and '/'
    alphabet = string.ascii_letters + string.digits + '+/'

    # Generate the password
    return ''.join(secrets.choice(alphabet) for i in range(password_length))


def generate_cloud_init(base_work_dir):
    kubeadmin_pass = generate_random_password()
    unused_developer_pass = generate_random_password()
    pub_key = remote_access.read(base_work_dir / "crc" / "machine" / "id_ecdsa_crc.pub")
    pull_secret = config.project.get_config("prepare.openshift.pull_secret", handled_secretly=True)

    generate_cloud_init_file(base_work_dir, pull_secret, pub_key, kubeadmin_pass, unused_developer_pass)


def get_cloud_init_files(base_work_dir):
    user_data = base_work_dir / "crc" / "cloud-init" / "user-data"
    meta_data = user_data.parent / "meta-data"
    return user_data, meta_data


def generate_cloud_init_file(base_work_dir, pull_secret, pub_key, pass_kubeadmin, pass_developer):
    cloud_init_text_content = (TESTING_THIS_DIR / "cloud-init.yaml").read_text()
    cloud_init_def = yaml.safe_load(cloud_init_text_content)

    for write_file in cloud_init_def["write_files"]:
        content = write_file.get("content")
        if content is None:
            pass # content field not set
        elif content == "$PUB_KEY":
            write_file["content"] = pub_key + "\n"
        elif content == "$PULL_SECRET":
            write_file["content"] = pull_secret + "\n"
        elif content == "$PASS_KUBEADMIN":
            write_file["content"] = pass_kubeadmin.strip()
        elif content == "$PASS_DEVELOPER":
            write_file["content"] = pass_developer.strip()

    cloud_init_content = "#cloud-config\n\n"+yaml.dump(cloud_init_def)

    user_data, meta_data = get_cloud_init_files(base_work_dir)
    remote_access.mkdir(user_data.parent)
    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"touch '{meta_data}'")
    remote_access.write(user_data, cloud_init_content, handled_secretly=True)
    logging.info(f"Cloud-init file generated in {user_data} ...")


def prepare():
    base_work_dir = remote_access.prepare()
    remote_access.mkdir(env.ARTIFACT_DIR)

    prepare_crc_bundle(base_work_dir)

    generate_cloud_init(base_work_dir)

    prepare_crc_binary(base_work_dir)

    return 0
