from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats

import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report

# TODO: print exec error when need password
# TODO: fix graphs


def register():
    CPUUsageReport()
    NetworkUsageReport()
    DiskUsageReport()
    PowerUsageReport()
    TimeBenchReport()


class CPUUsageReport():
    def __init__(self):
        self.name = "report: CPU Usage"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        plot_name = "System CPU Usage"
        header += [html.H1(plot_name)]
        header += report.Plot_and_Text(plot_name, args)

        return None, header


class NetworkUsageReport():
    def __init__(self):
        self.name = "report: Network Usage"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        plot_name = "System Network Usage"
        header += [html.H1(plot_name)]
        header += report.Plot_and_Text(plot_name, args)

        return None, header


class DiskUsageReport():
    def __init__(self):
        self.name = "report: Disk Usage"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        plot_name = "System Disk Usage"
        header += [html.H1(plot_name)]
        header += report.Plot_and_Text(plot_name, args)

        return None, header


class PowerUsageReport():
    def __init__(self):
        self.name = "report: Power Usage"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []

        plot_name = "System Power Usage"
        header += [html.H1(plot_name)]
        header += report.Plot_and_Text(plot_name, args)

        return None, header


class TimeBenchReport():
    def __init__(self):
        self.name = "report: Execution Time"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []

        header += [html.H1("Execution Time results")]

        ordered_vars, settings, setting_lists, variables, cfg = args

        if not len(ordered_vars) == 1:
            header += [
                html.B(
                    "Cannot generate the performance comparison with more than 1 variable" +
                    f" (got: {', '.join(ordered_vars)})"
                )
            ]
            return None, header

        """
        for group in "compute", "transfer":

            header += [html.H2(f"Performance Comparisons of the <i>{group}</i> operations")]

            # take all the possibilities two by two
            first_vars = variables[ordered_vars[0]]
            for ref, comp in (itertools.combinations(first_vars, 2)):
                header += report.Plot_and_Text(
                    "Llama-micro-bench comparison plot",
                    report.set_config(dict(group=group, ref=ref, comp=comp), args)
                )
        """
        return None, header
