from enum import Enum
from projects.core.library import config


class SystemType(Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    DARWIN = "darwin"


class ConfigKeys:
    REMOTE_HOST_SYSTEM = "remote_host.system"
    REMOTE_HOST_BASE_WORK_DIR = "remote_host.base_work_dir"
    REMOTE_HOST_PODMAN_BIN = "remote_host.podman_bin"
    REMOTE_HOST_DOCKER_BIN = "remote_host.docker.docker_bin"

    # Podman configuration
    PODMAN_REPO_ENABLED = "prepare.podman.repo.enabled"
    PODMAN_REPO_VERSION = "prepare.podman.repo.version"
    PODMAN_REPO_URL = "prepare.podman.repo.url"
    PODMAN_MACHINE_ENABLED = "prepare.podman.machine.enabled"
    PODMAN_MACHINE_NAME = "prepare.podman.machine.name"
    PODMAN_MACHINE_ENV = "prepare.podman.machine.env"
    PODMAN_MACHINE_FORCE_CONFIGURATION = "prepare.podman.machine.force_configuration"
    PODMAN_MACHINE_SET_DEFAULT = "prepare.podman.machine.set_default"
    PODMAN_MACHINE_CONFIGURATION = "prepare.podman.machine.configuration"
    PODMAN_MACHINE_CONFIGURATION_ROOTFUL = "prepare.podman.machine.configuration.rootful"
    PODMAN_MACHINE_ENV_CONTAINERS_MACHINE_PROVIDER = "prepare.podman.machine.env.CONTAINERS_MACHINE_PROVIDER"
    PODMAN_LINUX_ROOTFUL = "prepare.podman.linux.rootful"
    PODMAN_LINUX_RUNTIME = "prepare.podman.linux.runtime"

    # Custom binary configuration
    CUSTOM_BINARY_ENABLED = "prepare.podman.custom_binary.enabled"
    CUSTOM_BINARY_CLIENT_FILE = "prepare.podman.custom_binary.client_file"
    CUSTOM_BINARY_SERVER_FILE = "prepare.podman.custom_binary.server_file"
    CUSTOM_BINARY_URL = "prepare.podman.custom_binary.url"

    # Test configuration
    TEST_MATBENCHMARKING_ENABLED = "test.matbenchmarking.enabled"
    TEST_PLATFORM = "test.platform"
    TEST_PLATFORMS_TO_SKIP = "test.platforms_to_skip"
    TEST_BENCHMARK = "test.benchmark"
    TEST_MATBENCHMARKING_ITERABLE_TEST_FIELDS = "test.matbenchmarking.iterable_test_fields"
    TEST_MATBENCHMARKING_STOP_ON_ERROR = "test.matbenchmarking.stop_on_error"
    TEST_MATBENCHMARKING_MAP_ITERABLE_TEST_FIELDS = "test.matbenchmarking.map_iterable_test_fields"
    TEST_CAPTURE_METRICS_ENABLED = "test.capture_metrics.enabled"

    # Cleanup configuration
    CLEANUP_FILES_PODMAN = "cleanup.files.podman"

    # MatBench configuration
    MATBENCH_ENABLED = "matbench.enabled"

    # Installation configuration
    PREPARE_BREW_INSTALL_DEPENDENCIES = "prepare.brew.install_dependencies"
    PREPARE_BREW_DEPENDENCIES = "prepare.brew.dependencies"
    PREPARE_DNF_INSTALL_DEPENDENCIES = "prepare.dnf.install_dependencies"
    PREPARE_DNF_ENABLE_DOCKER_REPO = "prepare.dnf.enable_docker_repo"
    PREPARE_DNF_DEPENDENCIES = "prepare.dnf.dependencies"
    PREPARE_CHOCO_INSTALL_DEPENDENCIES = "prepare.choco.install_dependencies"
    PREPARE_CHOCO_DEPENDENCIES = "prepare.choco.dependencies"
    PREPARE_CONTAINER_IMAGES_PULL_IMAGES = "prepare.container_images.pull_images"
    PREPARE_CONTAINER_IMAGES_IMAGES = "prepare.container_images.images"
    PREPARE_CONTAINER_IMAGES_IMAGES_DIR = "prepare.container_images.dir"

    # Additional cleanup configuration
    CLEANUP_FILES_EXEC_TIME = "cleanup.files.exec_time"
    CLEANUP_FILES_VENV = "cleanup.files.venv"
    CLEANUP_PODMAN_MACHINE_DELETE = "cleanup.podman_machine.delete"
    CLEANUP_DOCKER_SERVICE_STOP = "cleanup.docker_service.stop"
    CLEANUP_DOCKER_DESKTOP_STOP = "cleanup.docker_desktop.stop"
    CLEANUP_CONTAINER_IMAGES = "cleanup.files.container_images"

    # Additional remote host configuration
    REMOTE_HOST_DOCKER_ENABLED = "remote_host.docker.enabled"
    REMOTE_HOST_RUN_LOCALLY = "remote_host.run_locally"

    # Additional podman machine configuration
    PREPARE_PODMAN_MACHINE_USE_CONFIGURATION = "prepare.podman.machine.use_configuration"


class ConfigManager:
    @staticmethod
    def get_system_type():
        system_str = config.project.get_config(ConfigKeys.REMOTE_HOST_SYSTEM, print=False)
        try:
            return SystemType(system_str)
        except ValueError:
            raise ValueError(f"Unsupported system type: {system_str}")

    @staticmethod
    def is_windows():
        return ConfigManager.get_system_type() == SystemType.WINDOWS

    @staticmethod
    def is_linux():
        return ConfigManager.get_system_type() == SystemType.LINUX

    @staticmethod
    def get_podman_config():
        return {
            'repo_enabled': config.project.get_config(ConfigKeys.PODMAN_REPO_ENABLED, print=False),
            'repo_version': config.project.get_config(ConfigKeys.PODMAN_REPO_VERSION, print=False),
            'machine_enabled': config.project.get_config(ConfigKeys.PODMAN_MACHINE_ENABLED, print=False),
            'machine_name': config.project.get_config(ConfigKeys.PODMAN_MACHINE_NAME, print=False),
            'machine_env': config.project.get_config(ConfigKeys.PODMAN_MACHINE_ENV, print=False),
            'linux_rootful': config.project.get_config(ConfigKeys.PODMAN_LINUX_ROOTFUL, print=False),
            'linux_runtime': config.project.get_config(ConfigKeys.PODMAN_LINUX_RUNTIME, print=False),
        }

    @staticmethod
    def get_binary_path(engine):
        if engine == "podman":
            return config.project.get_config(ConfigKeys.REMOTE_HOST_PODMAN_BIN, print=False) or "podman"
        elif engine == "docker":
            return config.project.get_config(ConfigKeys.REMOTE_HOST_DOCKER_BIN, print=False) or "docker"
        else:
            raise ValueError(f"Unsupported engine: {engine}")

    @staticmethod
    def get_custom_binary_config():
        return {
            'enabled': config.project.get_config(ConfigKeys.CUSTOM_BINARY_ENABLED, print=False),
            'client_file': config.project.get_config(ConfigKeys.CUSTOM_BINARY_CLIENT_FILE, print=False),
            'server_file': config.project.get_config(ConfigKeys.CUSTOM_BINARY_SERVER_FILE, print=False),
            'url': config.project.get_config(ConfigKeys.CUSTOM_BINARY_URL, print=False),
        }

    @staticmethod
    def get_test_config():
        return {
            'matbenchmarking_enabled': config.project.get_config(
                ConfigKeys.TEST_MATBENCHMARKING_ENABLED, print=False),
            'platform': config.project.get_config(ConfigKeys.TEST_PLATFORM, print=False),
            'platforms_to_skip': config.project.get_config(ConfigKeys.TEST_PLATFORMS_TO_SKIP, print=False),
            'benchmark': config.project.get_config(ConfigKeys.TEST_BENCHMARK, print=False),
            'iterable_test_fields': config.project.get_config(
                ConfigKeys.TEST_MATBENCHMARKING_ITERABLE_TEST_FIELDS, print=False),
            'stop_on_error': config.project.get_config(
                ConfigKeys.TEST_MATBENCHMARKING_STOP_ON_ERROR, print=False),
            'map_iterable_test_fields': config.project.get_config(
                ConfigKeys.TEST_MATBENCHMARKING_MAP_ITERABLE_TEST_FIELDS, print=False),
            'capture_metrics_enabled': config.project.get_config(
                ConfigKeys.TEST_CAPTURE_METRICS_ENABLED, print=False),
        }

    @staticmethod
    def get_cleanup_config():
        return {
            'files_podman': config.project.get_config(ConfigKeys.CLEANUP_FILES_PODMAN, print=False),
        }

    @staticmethod
    def get_podman_machine_config():
        return {
            'rootful': config.project.get_config(ConfigKeys.PODMAN_MACHINE_CONFIGURATION_ROOTFUL, print=False),
            'force_configuration': config.project.get_config(
                ConfigKeys.PODMAN_MACHINE_FORCE_CONFIGURATION, print=False),
            'set_default': config.project.get_config(ConfigKeys.PODMAN_MACHINE_SET_DEFAULT, print=False),
            'name': config.project.get_config(ConfigKeys.PODMAN_MACHINE_NAME, print=False),
            'configuration': config.project.get_config(ConfigKeys.PODMAN_MACHINE_CONFIGURATION, print=False),
            'configuration_rootful': config.project.get_config(
                ConfigKeys.PODMAN_MACHINE_CONFIGURATION_ROOTFUL, print=False),
            'env_containers_machine_provider': config.project.get_config(
                ConfigKeys.PODMAN_MACHINE_ENV_CONTAINERS_MACHINE_PROVIDER, print=False),
        }

    @staticmethod
    def get_repo_file_for_system(system):
        return config.project.get_config(f"prepare.podman.repo.{system}.file", print=False)

    @staticmethod
    def get_benchmark_config(benchmark_name):
        return {
            'supported_container_engines': config.project.get_config(
                f"{benchmark_name}.supported_container_engines", print=False),
            'runs': config.project.get_config(f"{benchmark_name}.runs", print=False),
        }

    @staticmethod
    def is_matbench_enabled():
        return config.project.get_config(ConfigKeys.MATBENCH_ENABLED, print=False) or False

    @staticmethod
    def get_brew_config():
        return {
            'install_dependencies': config.project.get_config(
                ConfigKeys.PREPARE_BREW_INSTALL_DEPENDENCIES, print=False),
            'dependencies': config.project.get_config(ConfigKeys.PREPARE_BREW_DEPENDENCIES, print=False),
        }

    @staticmethod
    def get_dnf_config():
        return {
            'install_dependencies': config.project.get_config(
                ConfigKeys.PREPARE_DNF_INSTALL_DEPENDENCIES, print=False),
            'enable_docker_repo': config.project.get_config(
                ConfigKeys.PREPARE_DNF_ENABLE_DOCKER_REPO, print=False),
            'dependencies': config.project.get_config(ConfigKeys.PREPARE_DNF_DEPENDENCIES, print=False),
        }

    @staticmethod
    def get_choco_config():
        return {
            'install_dependencies': config.project.get_config(
                ConfigKeys.PREPARE_CHOCO_INSTALL_DEPENDENCIES, print=False),
            'dependencies': config.project.get_config(ConfigKeys.PREPARE_CHOCO_DEPENDENCIES, print=False),
        }

    @staticmethod
    def get_container_images_config():
        return {
            'pull_images': config.project.get_config(
                ConfigKeys.PREPARE_CONTAINER_IMAGES_PULL_IMAGES, print=False),
            'images': config.project.get_config(
                ConfigKeys.PREPARE_CONTAINER_IMAGES_IMAGES, print=False),
            'dir': config.project.get_config(
                ConfigKeys.PREPARE_CONTAINER_IMAGES_IMAGES_DIR, print=False),
        }

    @staticmethod
    def get_extended_cleanup_config():
        return {
            'files_exec_time': config.project.get_config(ConfigKeys.CLEANUP_FILES_EXEC_TIME, print=False),
            'files_venv': config.project.get_config(ConfigKeys.CLEANUP_FILES_VENV, print=False),
            'files_podman': config.project.get_config(ConfigKeys.CLEANUP_FILES_PODMAN, print=False),
            'podman_machine_delete': config.project.get_config(
                ConfigKeys.CLEANUP_PODMAN_MACHINE_DELETE, print=False),
            'docker_service_stop': config.project.get_config(
                ConfigKeys.CLEANUP_DOCKER_SERVICE_STOP, print=False),
            'docker_desktop_stop': config.project.get_config(
                ConfigKeys.CLEANUP_DOCKER_DESKTOP_STOP, print=False),
            'container_images': config.project.get_config(
                ConfigKeys.CLEANUP_CONTAINER_IMAGES, print=False),
        }

    @staticmethod
    def is_docker_enabled():
        return config.project.get_config(ConfigKeys.REMOTE_HOST_DOCKER_ENABLED, print=False) or False

    @staticmethod
    def should_use_podman_machine_configuration():
        return config.project.get_config(
            ConfigKeys.PREPARE_PODMAN_MACHINE_USE_CONFIGURATION, print=False) or False

    @staticmethod
    def should_run_locally():
        return config.project.get_config(ConfigKeys.REMOTE_HOST_RUN_LOCALLY, print=False) or False

    @staticmethod
    def validate_required_config():
        required_configs = [
            ConfigKeys.REMOTE_HOST_SYSTEM,
            ConfigKeys.REMOTE_HOST_BASE_WORK_DIR,
        ]

        missing = []
        for key in required_configs:
            if not config.project.get_config(key, print=False):
                missing.append(key)

        if missing:
            raise ValueError(f"Missing required configuration: {missing}")
