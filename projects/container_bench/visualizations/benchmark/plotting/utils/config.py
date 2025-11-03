import logging
import itertools
import matrix_benchmarking.common as common
from .shared import (
    ENGINE_INFO_FIELD_MAPPINGS,
    SYSTEM_INFO_FIELD_MAPPINGS,
    format_field_value,
    detect_linux_system,
    detect_windows_system
)

CONFIGURATION_EXCLUDED_KEYS = {
    "container_engine", "benchmark", "benchmark_runs", "stats",
    "test_mac_ai", "platform", "repo_version", "test.podman.machine_provider",
    "test.podman.repo_version", "test.docker.repo_version"
}

PODMAN_ENGINE = "podman"
DOCKER_ENGINE = "docker"

ENGINE_LABEL_FIELD_CONFIG = [
    ("Client_version", "Client"),
    ("Host_version", "Host"),
    ("Mode", "Rootless"),
    ("Runtime", "Runtime"),
    ("Host_cpu", "CPU"),
    ("Host_memory", "Memory"),
    ("Host_kernel", "Kernel")
]

SYSTEM_STATE_PATHS = {
    'software_overview': ['Software', 'System Software Overview'],
    'hardware_overview': ['Hardware', 'Hardware Overview'],
}

PODMAN_PATHS = {
    'client': ['Client'],
    'host': ['host'],
    'security': ['host', 'security'],
    'version': ['version'],
    'runtime': ['host', 'ociRuntime']
}

DOCKER_PATHS = {
    'client': ['ClientInfo'],
}


def normalize_configuration_key(key):
    normalized_key = key.replace("test.podman.", "").replace("test.docker.", "")
    if '.' in normalized_key:
        normalized_key = normalized_key.split('.')[-1]
    return normalized_key


def _safe_nested_get(data, path, default=""):
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _extract_container_engine_provider(test_config):
    provider_path = ["prepare", "podman", "machine", "env"]
    if isinstance(test_config, dict):
        yaml_root = test_config.get("yaml_file", {})
    else:
        yaml_root = getattr(test_config, "yaml_file", {})
    env_dict = _safe_nested_get(yaml_root, provider_path, {}) or {}
    return env_dict.get("CONTAINERS_MACHINE_PROVIDER", "")


def _extract_system_info(system_state):
    sys_info = {}

    software_path = SYSTEM_STATE_PATHS['software_overview']
    software_overview = _safe_nested_get(system_state, software_path, {})
    sys_info["OS_version"] = software_overview.get("System Version", "")
    sys_info["Kernel_version"] = software_overview.get("Kernel Version", "")

    hardware_path = SYSTEM_STATE_PATHS['hardware_overview']
    hardware_overview = _safe_nested_get(system_state, hardware_path, {})
    sys_info["CPU_model"] = hardware_overview.get("Chip", "")
    sys_info["CPU_cores"] = hardware_overview.get("Total Number of Cores", "")
    sys_info["Memory"] = hardware_overview.get("Memory", "")
    sys_info["Model_id"] = hardware_overview.get("Model Identifier", "")
    sys_info["Architecture"] = hardware_overview.get("Architecture", "")

    if "Apple" in sys_info["CPU_model"]:
        sys_info["Architecture"] = "Arm64"

    return sys_info


def _extract_podman_engine_info(container_engine_info, is_linux):
    engine_info = {"Container_engine_platform": PODMAN_ENGINE}

    if not is_linux:
        client = _safe_nested_get(container_engine_info, PODMAN_PATHS['client'], {})
        engine_info["Client_version"] = client.get("Version", "")

    host = _safe_nested_get(container_engine_info, PODMAN_PATHS['host'], {})
    security = _safe_nested_get(container_engine_info, PODMAN_PATHS['security'], {})
    version = _safe_nested_get(container_engine_info, PODMAN_PATHS['version'], {})
    runtime = _safe_nested_get(container_engine_info, PODMAN_PATHS['runtime'], {})

    engine_info.update({
        "Mode": security.get("rootless", ""),
        "Host_version": version.get("Version", ""),
        "Host_cpu": host.get("cpus", ""),
        "Host_memory": host.get("memTotal", ""),
        "Host_kernel": host.get("kernel", ""),
        "Runtime": runtime.get("name", "")
    })

    return engine_info


def _extract_docker_engine_info(container_engine_info, is_linux):
    engine_info = {"Container_engine_platform": DOCKER_ENGINE}

    if not is_linux:
        client = _safe_nested_get(container_engine_info, DOCKER_PATHS['client'], {})
        engine_info["Client_version"] = client.get("Version", "")

    engine_info.update({
        "Host_version": container_engine_info.get("ServerVersion", ""),
        "Host_cpu": container_engine_info.get("NCPU", ""),
        "Host_memory": container_engine_info.get("MemTotal", ""),
        "Host_kernel": container_engine_info.get("KernelVersion", ""),
        "Runtime": container_engine_info.get("DefaultRuntime", "")
    })

    return engine_info


def categorize_configuration_fields(configurations, field_map, info_extractor_func, field_formatter_func=None):
    shared_fields = {}
    varying_fields = {}

    for field_key in field_map:
        field_values = []

        for config in configurations:
            config_info = info_extractor_func(config)
            field_value = config_info.get(field_key, "N/A")

            if field_formatter_func:
                field_value = field_formatter_func(field_key, field_value)

            field_values.append(field_value)

        unique_values = list(set(field_values))
        if len(unique_values) == 1:
            shared_fields[field_key] = unique_values[0]
        else:
            varying_fields[field_key] = True

    return shared_fields, varying_fields


def GetInfo(settings):
    data = {}

    for entry in common.Matrix.filter_records(settings):
        metrics = entry.results.__dict__.get("metrics")
        if not metrics:
            continue

        data.update({
            "execution_time_95th_percentile": metrics.execution_time_95th_percentile,
            "jitter": metrics.execution_time_jitter,
            "command": metrics.command,
            "timestamp": metrics.timestamp,
            "runs": entry.settings.__dict__.get("benchmark_runs", 1)
        })

        test_config = entry.results.__dict__.get("test_config", {})
        if test_config:
            data["container_engine_provider"] = _extract_container_engine_provider(test_config)
        else:
            logging.warning("Missing test_config in entry results.")
            data["container_engine_provider"] = ""

        system_state = entry.results.__dict__.get("system_state")
        is_linux = False
        if system_state:
            sys_info = _extract_system_info(system_state)
            is_linux = detect_linux_system(sys_info)
            data["system"] = sys_info

        container_engine_info = entry.results.__dict__.get("container_engine_info")
        platform = entry.settings.__dict__.get("container_engine", "")

        if container_engine_info:
            data["container_engine_full"] = container_engine_info

            if platform == PODMAN_ENGINE:
                data["container_engine_info"] = _extract_podman_engine_info(container_engine_info, is_linux)
            elif platform == DOCKER_ENGINE:
                if detect_windows_system(data.get("system", {})):
                    data["container_engine_provider"] = "wsl"
                else:
                    data["container_engine_provider"] = "N/A (Docker)"
                data["container_engine_info"] = _extract_docker_engine_info(container_engine_info, is_linux)

        if is_linux:
            data.pop("container_engine_provider", None)

    return data


def generate_config_label(settings, exclude_benchmark=False):
    label_parts = []

    if "container_engine" in settings:
        label_parts.append(settings['container_engine'])

    if "benchmark" in settings and not exclude_benchmark:
        benchmark_name = settings['benchmark'].replace('_', ' ').title()
        label_parts.append(benchmark_name)

    for key in sorted(settings.keys()):
        if key not in ["container_engine", "benchmark"]:
            value = settings[key]
            if value is not None and value != "---":
                short_key = normalize_configuration_key(key)
                label_parts.append(f"{short_key}: {value}")

    return " | ".join(label_parts) if label_parts else "Configuration"


def _add_provider_info_if_varying(label_parts, config, all_configurations):
    provider = config.get("container_engine_provider")
    if not provider or provider == "N/A":
        return

    providers = [c.get("container_engine_provider") for c in all_configurations]
    unique_providers = set(p for p in providers if p and p != "N/A")

    if len(unique_providers) > 1:
        label_parts.append(f"Provider: {provider}")


def _add_engine_info_if_varying(label_parts, config, all_configurations):
    engine_info = config.get("container_engine_info", {})

    for field_key, short_name in ENGINE_LABEL_FIELD_CONFIG:
        value = engine_info.get(field_key)
        if not value or value == "N/A":
            continue

        all_values = []
        for check_config in all_configurations:
            check_engine_info = check_config.get("container_engine_info", {})
            check_value = check_engine_info.get(field_key)
            if check_value and check_value != "N/A":
                processed_check_value = format_field_value(field_key, check_value)
                all_values.append(processed_check_value)

        if len(set(all_values)) > 1:
            processed_value = format_field_value(field_key, value)

            if field_key == "Host_version":
                system_info = config.get("system", {})
                if detect_linux_system(system_info):
                    label_parts.append(f"Version: {processed_value}")
                else:
                    label_parts.append(f"{short_name}: {processed_value}")
            else:
                label_parts.append(f"{short_name}: {processed_value}")


def _add_settings_if_varying(label_parts, config, all_configurations):
    settings = config.get("settings", {})

    for key in sorted(settings.keys()):
        if key in CONFIGURATION_EXCLUDED_KEYS:
            continue

        value = settings[key]
        if value is None or value == "---":
            continue

        all_setting_values = []
        for other_config in all_configurations:
            other_settings = other_config.get("settings", {})
            other_value = other_settings.get(key)
            if other_value is not None and other_value != "---":
                all_setting_values.append(other_value)

        if len(set(all_setting_values)) > 1:
            short_key = normalize_configuration_key(key)
            label_parts.append(f"{short_key}: {value}")


def generate_display_config_label(config, all_configurations):
    if all_configurations is None:
        all_configurations = [config]

    label_parts = []
    settings = config.get("settings", {})

    if "container_engine" in settings:
        label_parts.append(settings['container_engine'])

    if len(all_configurations) > 1:
        _add_provider_info_if_varying(label_parts, config, all_configurations)
        _add_engine_info_if_varying(label_parts, config, all_configurations)
        _add_settings_if_varying(label_parts, config, all_configurations)
    else:
        provider = config.get("container_engine_provider")
        if provider and provider != "N/A":
            label_parts.append(f"Provider: {provider}")

    return " | ".join(label_parts) if label_parts else "Configuration"


def get_all_configuration_info(settings, setting_lists):
    static_settings = {k: v for k, v in settings.items() if v != "---"}
    configurations_by_benchmark = {}

    setting_combinations = itertools.product(*setting_lists)
    sorted_combinations = sorted(setting_combinations, key=lambda x: x[0][0] if x else None)

    for settings_values in sorted_combinations:
        current_settings = dict(settings_values)
        current_settings.update(static_settings)

        for key in ["stats", "test_mac_ai"]:
            current_settings.pop(key, None)

        info = GetInfo(current_settings)
        if info:
            benchmark = current_settings.get("benchmark", "unknown")
            info["config_label"] = generate_config_label(current_settings, exclude_benchmark=True)
            info["settings"] = current_settings

            if benchmark not in configurations_by_benchmark:
                configurations_by_benchmark[benchmark] = []
            configurations_by_benchmark[benchmark].append(info)

    return configurations_by_benchmark


def find_shared_and_different_info(configurations):
    if len(configurations) <= 1:
        return {}, {}

    shared_info = {}
    different_info = {}

    system_field_map = {field: field for field in SYSTEM_INFO_FIELD_MAPPINGS.keys()}
    shared_system, different_system = categorize_configuration_fields(
        configurations, system_field_map, lambda config: config.get("system", {})
    )
    shared_info["system"] = shared_system
    different_info["system"] = different_system

    engine_field_map = {field: field for field in ENGINE_INFO_FIELD_MAPPINGS.keys()}
    shared_engine, different_engine = categorize_configuration_fields(
        configurations, engine_field_map, lambda config: config.get("container_engine_info", {}), format_field_value
    )
    shared_info["engine"] = shared_engine
    different_info["engine"] = different_engine

    common_fields = ["runs", "container_engine_provider", "container_engine", "command", "timestamp"]

    for field in common_fields:
        if field == "container_engine":
            values = [config.get("settings", {}).get("container_engine", "N/A") for config in configurations]
        else:
            values = [config.get(field, "N/A") for config in configurations]

        unique_values = list(set(values))
        if len(unique_values) == 1:
            shared_info[field] = unique_values[0]
        else:
            different_info[field] = True

    return shared_info, different_info
