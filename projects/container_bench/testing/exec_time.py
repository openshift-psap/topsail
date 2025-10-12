import subprocess
import time
import argparse
import sys
import psutil
import threading
import json
import logging
import datetime

DEFAULT_OUTPUT_FILE = "output.log"
DEFAULT_METRICS_LOG_FILE = "metrics.json"
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
        self.command = ""
        self.timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def to_dict(self):
        return {
            "cpu_usage": self.cpu_usage,
            "network_usage": self.network_usage,
            "disk_usage": self.disk_usage,
            "memory_usage": self.memory_usage,
            "interval": self.interval,
            "execution_time": self.execution_time,
            "return_code": self.return_code,
            "command": self.command,
            "timestamp": self.timestamp,
        }

    def set_execution_time(self, exec_time):
        self.execution_time = exec_time

    def set_return_code(self, return_code):
        self.return_code = return_code

    def set_command(self, command):
        self.command = command


def monitor_resources(stop_event, measurements):
    """
    Monitors system-wide CPU, network, disk, and memory usage in a separate thread.

    Args:
        stop_event (threading.Event): Signals when to stop monitoring.
        measurements (Measurements): Container used to store the collected data.
    """
    net_send_list = []
    net_recv_list = []
    disk_write_list = []
    disk_read_list = []

    try:
        last_net_io = psutil.net_io_counters()
        last_disk_io = psutil.disk_io_counters()
    except (psutil.AccessDenied, psutil.NoSuchProcess) as e:
        logging.warning(f"Could not initialize I/O counters: {e}")
        last_net_io = None
        last_disk_io = None

    while not stop_event.is_set():
        try:
            # Overall System CPU Usage
            cpu_percent = psutil.cpu_percent(interval=measurements.interval)
            measurements.cpu_usage.append(cpu_percent)

            # --- Network Usage ---
            if last_net_io is not None:
                try:
                    current_net_io = psutil.net_io_counters()
                    bytes_sent = max(0, current_net_io.bytes_sent - last_net_io.bytes_sent)
                    bytes_recv = max(0, current_net_io.bytes_recv - last_net_io.bytes_recv)
                    net_send_list.append(bytes_sent)
                    net_recv_list.append(bytes_recv)
                    last_net_io = current_net_io
                except (psutil.AccessDenied, psutil.NoSuchProcess) as e:
                    logging.warning(f"Network monitoring failed: {e}")
                    net_send_list.append(0)
                    net_recv_list.append(0)

            # --- Disk I/O ---
            if last_disk_io is not None:
                try:
                    current_disk_io = psutil.disk_io_counters()
                    read_bytes = max(0, current_disk_io.read_bytes - last_disk_io.read_bytes)
                    write_bytes = max(0, current_disk_io.write_bytes - last_disk_io.write_bytes)
                    disk_read_list.append(read_bytes)
                    disk_write_list.append(write_bytes)
                    last_disk_io = current_disk_io
                except (psutil.AccessDenied, psutil.NoSuchProcess) as e:
                    logging.warning(f"Disk monitoring failed: {e}")
                    disk_read_list.append(0)
                    disk_write_list.append(0)

            # --- Memory Usage ---
            try:
                memory_percent = psutil.virtual_memory().percent
                measurements.memory_usage.append(memory_percent)
            except (psutil.AccessDenied, psutil.NoSuchProcess) as e:
                logging.warning(f"Memory monitoring failed: {e}")
                measurements.memory_usage.append(0)

        except Exception as e:
            logging.error(f"Unexpected error in resource monitoring: {e}")
            # Continue monitoring but add zero values
            measurements.cpu_usage.append(0)
            net_send_list.append(0)
            net_recv_list.append(0)
            disk_read_list.append(0)
            disk_write_list.append(0)
            measurements.memory_usage.append(0)

    measurements.network_usage["send"] = net_send_list
    measurements.network_usage["recv"] = net_recv_list
    measurements.disk_usage["read"] = disk_read_list
    measurements.disk_usage["write"] = disk_write_list


def execute_command(command_list, stop_event, monitor_thread):
    """
    Executes a command and captures its output, error, and execution time.

    Args:
        command_list (list): A list of strings representing the command and its arguments.
        stop_event (threading.Event): Signals the monitor thread to stop.
        monitor_thread (threading.Thread): Thread sampling CPU/net/disk/memory.

    Returns:
        tuple: (stdout, stderr, return_code, execution_time)
               stdout (str): Standard output of the command.
               stderr (str): Standard error of the command.
               return_code (int): Return code of the command.
               execution_time (float): Time taken to execute the command in seconds.
    """
    stdout = ""
    stderr = ""
    return_code = -1
    end_time = None

    try:
        monitor_thread.start()
    except RuntimeError as e:
        logging.error(f"Failed to start monitoring thread: {e}")

    start_time = time.perf_counter()

    try:
        if not command_list or not all(isinstance(cmd, str) for cmd in command_list):
            raise ValueError("Command list must be non-empty and contain only strings")

        with subprocess.Popen(
            command_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        ) as process:
            try:
                stdout, stderr = process.communicate(timeout=3600)  # 1 hour timeout
                return_code = process.returncode
            except subprocess.TimeoutExpired:
                logging.error("Command execution timed out after 1 hour")
                process.kill()
                stdout, stderr = process.communicate()
                return_code = -1
                stderr = f"Command timed out after 1 hour\n{stderr}"

        end_time = time.perf_counter()

    except FileNotFoundError as e:
        error_msg = f"Command not found: {command_list[0]} - {e}"
        logging.error(error_msg)
        stderr = error_msg
        return_code = 127
        end_time = time.perf_counter()

    except PermissionError as e:
        error_msg = f"Permission denied executing: {command_list[0]} - {e}"
        logging.error(error_msg)
        stderr = error_msg
        return_code = 126
        end_time = time.perf_counter()

    except Exception as e:
        error_msg = f"Unexpected error executing command: {e}"
        logging.error(error_msg)
        stderr = error_msg
        return_code = -1
        end_time = time.perf_counter()

    finally:
        stop_event.set()
        try:
            if monitor_thread.is_alive():
                monitor_thread.join(timeout=5.0)  # Wait max 5 seconds
                if monitor_thread.is_alive():
                    logging.warning("Monitoring thread did not stop gracefully")
        except Exception as e:
            logging.warning(f"Error stopping monitoring thread: {e}")

    execution_time = (end_time or time.perf_counter()) - start_time
    return stdout, stderr, return_code, execution_time


def write_to_file(filepath, content):
    with open(filepath, 'a') as f:
        f.write(content)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )

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
        "--metrics-log-file",
        default=DEFAULT_METRICS_LOG_FILE,
        help=f"File to log the metrics during run of command (default: {DEFAULT_METRICS_LOG_FILE})"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        logging.error("\nError: No command provided.")
        sys.exit(1)

    measurements = Measurements(interval=DEFAULT_INTERVAL)
    stop_event = threading.Event()

    command_to_run = args.command

    monitor_thread = threading.Thread(
        target=monitor_resources,
        args=(stop_event, measurements),
        daemon=True
    )

    stdout, stderr, return_code, exec_time = execute_command(
        command_to_run,
        stop_event,
        monitor_thread
    )

    measurements.set_execution_time(exec_time)
    measurements.set_return_code(return_code)
    measurements.set_command(' '.join(command_to_run))

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

    write_to_file(args.metrics_log_file, json.dumps(measurements.to_dict(), separators=(',', ':')) + "\n")

    if return_code != 0:
        logging.warning(f"Command exited with return code {return_code}")
        logging.warning(f"STDERR: {stderr}")
        sys.exit(return_code)


if __name__ == "__main__":
    main()
