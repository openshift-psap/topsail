from math import log


def human_readable_size(value):
    """Convert a byte value to a human-readable string.

    Args:
        value (int): The byte value to convert.

    Returns:
        str: The human-readable string representation of the byte value.
    """
    if value is None:
        return "N/A"

    suffix = [" kB", " MB", " GB", " TB", " PB", " EB", " ZB", " YB", " RB", " QB"]
    base = 1000
    bytes_ = float(value)
    abs_bytes = abs(bytes_)
    if abs_bytes == 1:
        return f"{int(bytes_)} Byte"
    elif abs_bytes < base:
        return f"{int(bytes_)} Bytes"
    exp = int(min(log(abs_bytes, base), len(suffix)))
    return f"{(bytes_ / (base**exp)):.1f}{suffix[exp - 1]}"


def format_duration(seconds):
    """Convert a duration in seconds to a human-readable string.

    Args:
        seconds (float): The duration in seconds.

    Returns:
        str: The human-readable string representation of the duration.
    """
    if seconds is None:
        return "N/A"
    if seconds < 1e-6:
        return f"{seconds * 1e9:.2f} ns"
    if seconds < 1e-3:
        return f"{seconds * 1e6:.2f} µs"
    if seconds < 1:
        return f"{seconds * 1e3:.2f} ms"

    return f"{seconds:.2f} s"
