import matrix_benchmarking.common as common

BYTES_TO_MEGABYTES = 1024 * 1024

SUPPORTED_METRIC_TYPES = [
    'cpu', 'memory', 'network_send', 'network_recv', 'disk_read', 'disk_write'
]

METRIC_DISPLAY_CONFIG = {
    'cpu': ('Average CPU Usage', '%'),
    'memory': ('Average Memory Usage', '%'),
    'network_send': ('Average Network Send', 'MB/s'),
    'network_recv': ('Average Network Recv', 'MB/s'),
    'disk_read': ('Average Disk Read', 'MB/s'),
    'disk_write': ('Average Disk Write', 'MB/s')
}

METRIC_CALCULATION_CONFIG = {
    'cpu': {'type': 'simple', 'attribute': 'cpu'},
    'memory': {'type': 'simple', 'attribute': 'memory'},
    'network_send': {'type': 'network', 'direction': 'send'},
    'network_recv': {'type': 'network', 'direction': 'recv'},
    'disk_read': {'type': 'disk', 'operation': 'read'},
    'disk_write': {'type': 'disk', 'operation': 'write'}
}


def compute_metric_average(metrics, metric_type, interval=1):
    if metric_type not in METRIC_CALCULATION_CONFIG:
        return None

    config = METRIC_CALCULATION_CONFIG[metric_type]
    calc_type = config['type']

    if calc_type == 'simple':
        return _calculate_simple_average(metrics, config['attribute'])
    elif calc_type == 'network':
        return _calculate_throughput_average(metrics, calc_type, config['direction'], interval)
    elif calc_type == 'disk':
        return _calculate_throughput_average(metrics, calc_type, config['operation'], interval)
    return None


def _calculate_simple_average(metrics, attribute_name):
    data = getattr(metrics, attribute_name, None)
    if not data or not isinstance(data, (list, tuple)):
        return None

    try:
        return sum(data) / len(data)
    except (TypeError, ZeroDivisionError):
        return None


def _calculate_throughput_average(metrics, container_attr, data_key, interval):
    container = getattr(metrics, container_attr, None)
    if not container or not isinstance(container, dict):
        return None

    data = container.get(data_key, [])
    if not data or not isinstance(data, (list, tuple)):
        return None

    try:
        mb_per_second = [(item / BYTES_TO_MEGABYTES) / interval for item in data]
        return sum(mb_per_second) / len(mb_per_second)
    except (TypeError, ZeroDivisionError, ValueError):
        return None


def calculate_config_metrics(settings):
    entries = common.Matrix.filter_records(settings)
    if not entries:
        return {}

    config_averages = {}

    for entry in entries:
        metrics = entry.results.__dict__.get("metrics")
        if not metrics:
            continue

        interval = getattr(metrics, 'interval', 1)

        for metric_type in SUPPORTED_METRIC_TYPES:
            avg_value = compute_metric_average(metrics, metric_type, interval)
            if avg_value is not None:
                config_averages[metric_type] = avg_value

    return config_averages


def _extract_metric_values(usage_averages, metric):
    metric_values = []
    metric_labels = []

    for config_label, averages in usage_averages.items():
        if metric in averages:
            metric_values.append(averages[metric])
            metric_labels.append(config_label)

    return metric_values, metric_labels


def _calculate_metric_delta(metric_values, metric_labels):
    if len(metric_values) < 2:
        return None

    min_val = min(metric_values)
    max_val = max(metric_values)
    delta = max_val - min_val

    min_idx = metric_values.index(min_val)
    max_idx = metric_values.index(max_val)

    return {
        'delta': delta,
        'min_value': min_val,
        'max_value': max_val,
        'min_config': metric_labels[min_idx],
        'max_config': metric_labels[max_idx],
        'percentage': (delta / min_val * 100) if min_val > 0 else 0
    }


def calculate_usage_deltas(configurations):
    if len(configurations) < 2:
        return {}

    usage_averages = {}
    for config in configurations:
        config_label = config.get("config_label", "Unknown")
        settings = config.get("settings", {})
        config_averages = calculate_config_metrics(settings)
        usage_averages[config_label] = config_averages

    deltas = {}
    for metric in SUPPORTED_METRIC_TYPES:
        metric_values, metric_labels = _extract_metric_values(usage_averages, metric)
        delta_stats = _calculate_metric_delta(metric_values, metric_labels)

        if delta_stats:
            deltas[metric] = delta_stats

    return deltas
