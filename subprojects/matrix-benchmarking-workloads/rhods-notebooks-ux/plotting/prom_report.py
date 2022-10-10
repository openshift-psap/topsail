from dash import html

from . import report
import matrix_benchmarking.plotting.table_stats as table_stats

def register():
    RhodsCpuMemoryReport()
    DriverCpuMemoryReport()
    AuthenticationReport()
    RhodsReport()

def add_pod_cpu_mem_usage(header, what, args):
    header += [html.H2(f"{what} CPU and Memory usage")]
    header += [report.Plot(f"Prom: {what}: Mem usage", args)]
    header += [report.Plot(f"Prom: {what}: CPU usage", args)]

    header += [f"These plots show the CPU and memory usage of {what} Pods. "]
    header += ["The ", html.Code("requests"), " and ", html.Code("limits"),
                   " values are shown with a dashed line, ", html.I("if they are defined"), " in the Pod spec."]
    header += html.Br()
    header += html.Br()


class RhodsCpuMemoryReport():
    def __init__(self):
        self.name = "report: RHODS Cluster CPU/Memory Usage"
        self.id_name = self.name.lower().replace("/", "-")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.P("These plots show an overview of the CPU and Memory usage during the execution of the test, for the cluster, the nodes, and various relevant Pods.")]

        header += [html.H2("RHODS Cluster")]
        header += [report.Plot("Prom: sutest cluster memory usage", args)]
        header += [report.Plot("Prom: sutest cluster CPU usage", args)]

        header += ["These plots show the CPU and memory capacity of the RHODS cluster."]
        header += html.Br()
        header += html.Br()

        for what in "Notebooks", "RHODS Dashboard", "KF Notebook Controller", "ODH Notebook Controller":
            add_pod_cpu_mem_usage(header, what, args)

        return None, header


class DriverCpuMemoryReport():
    def __init__(self):
        self.name = "report: Driver Cluster CPU/Memory Usage"
        self.id_name = self.name.lower().replace("/", "-")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.P("These plots show an overview of the CPU and Memory usage during the execution of the test, for the cluster, the nodes, and various relevant Pods.")]

        header += [html.H2("Test-Driver Cluster")]
        header += [report.Plot("Prom: driver cluster memory usage", args)]
        header += [report.Plot("Prom: driver cluster CPU usage", args)]

        header += ["These plots show the CPU and memory capacity of the Test-Driver cluster."]
        header += html.Br()
        header += html.Br()

        for what in ["Test Pods"]:
            add_pod_cpu_mem_usage(header, what, args)


        return None, header


class AuthenticationReport():

    def __init__(self):
        self.name = "report: Authentication System"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.P("These plots show an overview the Authentication metrics.")]

        for what in  "OpenLDAP", "OpenShift Authentication":
            add_pod_cpu_mem_usage(header, what, args)

        header += [html.H2("Authentication Metrics")]
        header += [report.Plot("OCP: Form Auth Metrics", args)]
        header += [report.Plot("OCP: Basic Auth Metrics", args)]

        return None, header

class RhodsReport():
    def __init__(self):
        self.name = "report: RHODS metrics"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.P("These plots show an overview the RHODS metrics.")]

        plots = [
            ("RHODS: User Count and Joining Rate", "This plot shows the number of RHODS users, and the rate of new user creations, per minute."),
            ("RHODS: Pods CPU Usage", "This plot shows the CPU usage of the RHODS Pods, as exposed in RHODS prometheus. (May be incomplete.)"),
            ("RHODS: Pods Memory Usage", "This plot shows the memory usage (virtual and resident memory), as exposed in RHODS prometheus."),
            ("RHODS: Notebooks PVC Disk Usage", "This plot shows the disk usage of the user's PVCs, grouped by nodes."),
            ("RHODS: Reasons Why Notebooks Are Waiting", "This plot shows the number of Notebook Pods waiting for execution."),
        ]

        for (plot_name, description) in plots:
            header += [report.Plot(plot_name, args)]
            header += [html.P(description)]

        return None, header
