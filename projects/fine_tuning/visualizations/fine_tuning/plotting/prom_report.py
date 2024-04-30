from dash import html

from . import report
import matrix_benchmarking.plotting.table_stats as table_stats


def register():
    SutestCpuMemoryReport()
    ControlPlaneReport()


class SutestCpuMemoryReport():
    def __init__(self):
        self.name = "report: Sutest Cluster CPU/Memory Usage"
        self.id_name = self.name.lower().replace("/", "-")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.P("These plots show an overview of the CPU and Memory usage during the execution of the test, for the cluster, the nodes, and various relevant Pods.")]

        header += [html.H2("SUTest Cluster")]
        header += [report.Plot("Prom: sutest cluster memory usage", args)]
        header += [report.Plot("Prom: sutest cluster CPU usage", args)]

        header += ["These plots show the CPU and memory capacity of the SUTest cluster."]
        header += html.Br()
        header += html.Br()

        return None, header


class ControlPlaneReport():
    def __init__(self):
        self.name = "report: Control Plane Nodes Load"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.H1("Control Plane Nodes Load")]

        for cluster_role in ["sutest"]:
            header += [html.H1(f"{cluster_role.title()} cluster")]

            header += ["These plots shows the CPU and memory usage of the Kubernetes API Server and ETCD, running on the Control Plane nodes of the cluster."]

            for pod_name in ["ApiServer", "ETCD"]:
                header += [html.H2(f"{pod_name} subsystem")]

                for what in ["CPU", "Mem"]:
                    header += report.Plot_and_Text(f"Prom: {cluster_role.title()} {pod_name}: {what} usage", args)
                    header += html.Br()
                    header += html.Br()

            if cluster_role != "sutest": continue

            header += [html.H2(f"CPU usage")]

            header += ["These plots shows the CPU usage of the Control Plane nodes.",
                       html.Br(),
                       "The first plot show all the available modes, while the second one shows only the idle time (higher is better).",
                       html.Br(),
                       "The Y scale is arbitrary, but for a given node, the sum of all the modes at a given time indicate 100% of the CPU."
                       ]

            header += report.Plot_and_Text(f"Prom: {cluster_role.title()} Control Plane Node CPU usage", args)
            header += html.Br()
            header += html.Br()

            header += report.Plot_and_Text(f"Prom: {cluster_role.title()} Control Plane Node CPU idle", args)
            header += html.Br()
            header += html.Br()

            header += report.Plot_and_Text(f"Prom: {cluster_role.title()} Worker Node CPU usage", args)
            header += html.Br()
            header += html.Br()

            header += report.Plot_and_Text(f"Prom: {cluster_role.title()} Worker Node CPU idle", args)
            header += html.Br()
            header += html.Br()

            header += [html.H2(f"APIServer requests duration")]
            for verb in ["LIST", "GET", "PUT", "PATCH"]:
                header += report.Plot_and_Text(f"Prom: {cluster_role.title()} API Server {verb} Requests duration", args)
                header += html.Br()
                header += html.Br()

            header += [html.H2(f"API Server HTTP return codes")]
            for what in ["successes", "client errors", "server errors"]:
                header += report.Plot_and_Text(f"Prom: {cluster_role.title()} API Server Requests ({what})", args)
                header += html.Br()
                header += html.Br()

        return None, header
