from dash import html

import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

from .utils import check_prometheus_data_availability


def register():
    """Register all Prometheus report classes"""
    PrometheusResourceUsageReport()
    PrometheusGPUPerformanceReport()
    PrometheusSystemHealthReport()


class PrometheusResourceUsageReport():
    def __init__(self):
        self.name = "report: Prometheus Resource Usage"
        self.id_name = self.name.lower().replace(" ", "_").replace("-", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, *args):
        """
        Generate comprehensive resource usage report from Prometheus metrics
        """
        ordered_vars, settings, setting_lists, variables, cfg = args
        entries = list(common.Matrix.all_records(settings, setting_lists))

        header = []
        header.append(html.H2("📊 Resource Usage Analytics"))
        header.append(html.P("Comprehensive CPU and memory usage analysis for LLM-D inference workloads"))
        header.append(html.Br())

        if not entries:
            header.append(html.P("No test entries found."))
            return None, header

        # Check if main Prometheus metrics data is available
        has_data, error_elements = check_prometheus_data_availability("sutest", "resource usage report")
        if not has_data:
            header.extend(error_elements)
            return None, header

        # Application Resource Usage Section
        header.append(html.H3("🚀 LLM-D Application Resources"))
        header.append(html.P("CPU and memory usage for LLM-D inference services"))

        header += report.Plot_and_Text("Prom: LLM Inference Service: CPU usage", args)
        header += report.Plot_and_Text("Prom: LLM Inference Service: Mem usage", args)
        header += report.Plot_and_Text("Prom: LLM Inference Gateway: CPU usage", args)
        header += report.Plot_and_Text("Prom: LLM Inference Gateway: Mem usage", args)

        header.append(html.Br())

        # Cluster Resource Usage Section
        header.append(html.H3("🏗️ Cluster Resource Overview"))
        header.append(html.P("Overall cluster CPU and memory utilization"))

        header += report.Plot_and_Text("Prom: sutest cluster CPU usage", args)
        header += report.Plot_and_Text("Prom: sutest cluster memory usage", args)

        header.append(html.Br())

        # Node-level Resource Usage Section
        header.append(html.H3("🖥️ Node-level Resource Usage"))
        header.append(html.P("CPU usage and idle time breakdown by node type"))

        header += report.Plot_and_Text("Prom: Sutest Control Plane Node CPU usage", args)
        header += report.Plot_and_Text("Prom: Sutest Worker Node CPU usage", args)
        header += report.Plot_and_Text("Prom: Sutest Control Plane Node CPU idle", args)
        header += report.Plot_and_Text("Prom: Sutest Worker Node CPU idle", args)

        return None, header


class PrometheusGPUPerformanceReport():
    def __init__(self):
        self.name = "report: Prometheus GPU Performance"
        self.id_name = self.name.lower().replace(" ", "_").replace("-", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, *args):
        """
        Generate comprehensive GPU performance report from Prometheus DCGM metrics
        """
        ordered_vars, settings, setting_lists, variables, cfg = args
        entries = list(common.Matrix.all_records(settings, setting_lists))

        header = []
        header.append(html.H2("🎮 GPU Performance Analytics"))
        header.append(html.P("Comprehensive GPU utilization, memory, and throughput analysis using DCGM metrics"))
        header.append(html.Br())

        if not entries:
            header.append(html.P("No test entries found."))
            return None, header

        # Check if main Prometheus metrics data is available
        has_data, error_elements = check_prometheus_data_availability("sutest", "GPU performance report")
        if not has_data:
            header.extend(error_elements)
            return None, header

        # GPU Memory Usage Section
        header.append(html.H3("💾 GPU Memory Utilization"))
        header.append(html.P("GPU memory consumption and allocation patterns"))

        header += report.Plot_and_Text("Prom: Sutest GPU memory used", args)
        header += report.Plot_and_Text("Prom: Sutest GPU memory used (all GPUs)", args)
        header += report.Plot_and_Text("Prom: Sutest GPU memory unallocated", args)
        header += report.Plot_and_Text("Prom: Sutest GPU memory transfer utilization", args)

        header.append(html.Br())

        # GPU Compute Performance Section
        header.append(html.H3("⚡ GPU Compute Performance"))
        header.append(html.P("GPU compute utilization and active processing units"))

        header += report.Plot_and_Text("Prom: Sutest GPU compute utilization (not 100% accurate)", args)
        header += report.Plot_and_Text("Prom: Sutest GPU engine usage (not 100% accurate)", args)
        header += report.Plot_and_Text("Prom: Sutest GPU active computes", args)
        header += report.Plot_and_Text("Prom: Sutest GPU computes occupancy", args)

        header.append(html.Br())

        # GPU Pipeline Usage Section
        header.append(html.H3("🔧 GPU Pipeline Utilization"))
        header.append(html.P("GPU floating-point pipeline usage by precision"))

        header += report.Plot_and_Text("Prom: Sutest GPU active fp16 pipe", args)
        header += report.Plot_and_Text("Prom: Sutest GPU active fp32 pipe", args)
        header += report.Plot_and_Text("Prom: Sutest GPU active fp64 pipe", args)

        header.append(html.Br())

        # GPU Interconnect Performance Section
        header.append(html.H3("🔗 GPU Interconnect Performance"))
        header.append(html.P("NVLink and PCIe transfer rates and throughput"))

        header += report.Plot_and_Text("Prom: Sutest GPU NVLink transfer (rx)", args)
        header += report.Plot_and_Text("Prom: Sutest GPU NVLink transfer (tx)", args)
        header += report.Plot_and_Text("Prom: Sutest GPU PCIe transfer (rx)", args)
        header += report.Plot_and_Text("Prom: Sutest GPU PCIe transfer (tx)", args)

        return None, header


class PrometheusSystemHealthReport():
    def __init__(self):
        self.name = "report: Prometheus System Health"
        self.id_name = self.name.lower().replace(" ", "_").replace("-", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, *args):
        """
        Generate comprehensive system health report from Prometheus cluster metrics
        """
        ordered_vars, settings, setting_lists, variables, cfg = args
        entries = list(common.Matrix.all_records(settings, setting_lists))

        header = []
        header.append(html.H2("🏥 System Health Analytics"))
        header.append(html.P("Kubernetes cluster health monitoring including API server and ETCD performance"))
        header.append(html.Br())

        if not entries:
            header.append(html.P("No test entries found."))
            return None, header

        # Check if main Prometheus metrics data is available
        has_data, error_elements = check_prometheus_data_availability("sutest", "system health report")
        if not has_data:
            header.extend(error_elements)
            return None, header

        # API Server Performance Section
        header.append(html.H3("🔌 API Server Performance"))
        header.append(html.P("Kubernetes API server resource usage and request handling"))

        header += report.Plot_and_Text("Prom: Sutest ApiServer: CPU usage", args)
        header += report.Plot_and_Text("Prom: Sutest ApiServer: Mem usage", args)

        header.append(html.Br())

        # API Server Request Analysis Section
        header.append(html.H3("📈 API Server Request Analysis"))
        header.append(html.P("API request patterns, success rates, and error analysis"))

        header += report.Plot_and_Text("Prom: Sutest API Server Requests (successes)", args)
        header += report.Plot_and_Text("Prom: Sutest API Server Requests (client errors)", args)
        header += report.Plot_and_Text("Prom: Sutest API Server Requests (server errors)", args)

        header.append(html.Br())

        if False:
            # API Server Request Latency Section
            header.append(html.H3("⏱️ API Server Request Latency"))
            header.append(html.P("API request duration analysis by operation type"))

            header += report.Plot_and_Text("Prom: Sutest GET Requests duration", args)
            header += report.Plot_and_Text("Prom: Sutest PUT Requests duration", args)
            header += report.Plot_and_Text("Prom: Sutest LIST Requests duration", args)
            header += report.Plot_and_Text("Prom: Sutest PATCH Requests duration", args)

            header.append(html.Br())

        # ETCD Performance Section
        header.append(html.H3("🗄️ ETCD Performance"))
        header.append(html.P("ETCD cluster health and resource utilization"))

        header += report.Plot_and_Text("Prom: Sutest ETCD: CPU usage", args)
        header += report.Plot_and_Text("Prom: Sutest ETCD: Mem usage", args)

        return None, header
