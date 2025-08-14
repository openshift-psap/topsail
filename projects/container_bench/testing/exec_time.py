import subprocess
import time
import argparse
import sys
import psutil
import threading
import json

DEFAULT_OUTPUT_FILE = "output.txt"
DEFAULT_TIME_LOG_FILE = "time.log"
DEFAULT_METRICS_LOG_FILE = "metrics.log"
DEFAULT_INTERVAL = 0.5


class Measurements:
    def __init__(self, interval=DEFAULT_INTERVAL):
        self.cpu_usage = []
        self.network_usage = {"send": [], "recv": []}
        self.disk_usage = {"read": [], "write": []}
        self.memory_usage = []
        self.interval = interval
        self.execution_time = 0.0
        self.return_code = 0

    def to_dict(self):
        return {
            "cpu_usage": self.cpu_usage,
            "network_usage": self.network_usage,
            "disk_usage": self.disk_usage,
            "memory_usage": self.memory_usage,
            "interval": self.interval,
            "execution_time": self.execution_time,
            "return_code": self.return_code,
        }

    def set_execution_time(self, exec_time):
        self.execution_time = exec_time

    def set_return_code(self, return_code):
        self.return_code = return_code


def monitor_resources(stop_event, measurements):
    """
    Monitors system-wide CPU, network, disk, and memory usage in a separate thread.

    Args:
        stop_event (threading.Event): Signals when to stop monitoring.
        metrics (Metrics): An instance of the Metrics class to store the collected data.
    """
    net_send_list = []
    net_recv_list = []
    disk_write_list = []
    disk_read_list = []

    # Get initial network and disk counters
    last_net_io = psutil.net_io_counters()
    last_disk_io = psutil.disk_io_counters()

    while not stop_event.is_set():
        # Overall System CPU Usage
        measurements.cpu_usage.append(psutil.cpu_percent(interval=measurements.interval))

        # --- Network Usage ---
        current_net_io = psutil.net_io_counters()
        bytes_sent = current_net_io.bytes_sent - last_net_io.bytes_sent
        bytes_recv = current_net_io.bytes_recv - last_net_io.bytes_recv
        net_send_list.append(bytes_sent)
        net_recv_list.append(bytes_recv)
        last_net_io = current_net_io

        # --- Disk I/O ---
        current_disk_io = psutil.disk_io_counters()
        read_bytes = current_disk_io.read_bytes - last_disk_io.read_bytes
        write_bytes = current_disk_io.write_bytes - last_disk_io.write_bytes
        disk_read_list.append(read_bytes)
        disk_write_list.append(write_bytes)
        last_disk_io = current_disk_io

        # --- Memory Usage ---
        measurements.memory_usage.append(psutil.virtual_memory().percent)

    # Extend the lists with the collected data
    measurements.network_usage["send"] = net_send_list
    measurements.network_usage["recv"] = net_recv_list
    measurements.disk_usage["read"] = disk_read_list
    measurements.disk_usage["write"] = disk_write_list


def execute_command(command_list, stop_event, monitor_thread):
    """
    Executes a command and captures its output, error, and execution time.

    Args:
        command_list (list): A list of strings representing the command and its arguments.

    Returns:
        tuple: (stdout, stderr, return_code, execution_time)
               stdout (str): Standard output of the command.
               stderr (str): Standard error of the command.
               return_code (int): Return code of the command.
               execution_time (float): Time taken to execute the command in seconds.
    """
    monitor_thread.start()
    start_time = time.perf_counter()
    with subprocess.Popen(
        command_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    ) as process:
        stdout, stderr = process.communicate()
        process.wait()
    end_time = time.perf_counter()
    stop_event.set()
    monitor_thread.join()

    execution_time = end_time - start_time
    return_code = process.returncode

    return stdout, stderr, return_code, execution_time


def write_to_file(filepath, content):
    with open(filepath, 'a') as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser(
        description="Execute a command, log its execution time, and save its output.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="The command to execute and its arguments (e.g., ls -l /tmp or ping google.com -c 4)."
    )
    parser.add_argument(
        "--output-file",
        default=DEFAULT_OUTPUT_FILE,
        help=f"File to store the command's stdout and stderr (default: {DEFAULT_OUTPUT_FILE})"
    )
    parser.add_argument(
        "--time-log-file",
        default=DEFAULT_TIME_LOG_FILE,
        help=f"File to log the command's execution time (default: {DEFAULT_TIME_LOG_FILE})"
    )
    parser.add_argument(
        "--metrics-log-file",
        default=DEFAULT_METRICS_LOG_FILE,
        help=f"File to log the metrics during run of command (default: {DEFAULT_METRICS_LOG_FILE})"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print("\nError: No command provided.", file=sys.stderr)
        sys.exit(1)

    measurements = Measurements(interval=DEFAULT_INTERVAL)
    stop_event = threading.Event()

    command_to_run = args.command

    monitor_thread = threading.Thread(
        target=monitor_resources,
        args=(stop_event, measurements)
    )

    stdout, stderr, return_code, exec_time = execute_command(command_to_run, stop_event, monitor_thread)
    measurements.set_execution_time(exec_time)
    measurements.set_return_code(return_code)

    output_content = f"--- Command: {' '.join(command_to_run)} ---\n"
    output_content += f"Return Code: {return_code}\n\n"
    if stdout:
        output_content += "--- STDOUT ---\n"
        output_content += stdout
        output_content += "\n"
    if stderr:
        output_content += "--- STDERR ---\n"
        output_content += stderr
        output_content += "\n"
    output_content += "--- END ---\n\n"

    write_to_file(args.output_file, output_content)

    time_log_content = f"Command: \"{' '.join(command_to_run)}\"\n"
    time_log_content += f"ExecutionTime: {exec_time:.4f}s\n"
    time_log_content += f"ReturnCode: {return_code}\n"

    write_to_file(args.time_log_file, time_log_content)
    write_to_file(args.metrics_log_file, json.dumps(measurements.to_dict(), separators=(',', ':')) + "\n")

    if return_code != 0:
        print(f"\nWarning: Command exited with return code {return_code}", file=sys.stderr)


if __name__ == "__main__":
    main()
