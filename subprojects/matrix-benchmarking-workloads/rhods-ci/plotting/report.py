import copy

from dash import html
from dash import dcc

from matrix_benchmarking.common import Matrix
import matrix_benchmarking.plotting.table_stats as table_stats

def register():
    PriceOverviewReport()

    UserExecutionOverviewReport()
    TimelineReport()
    PodNodeMappingReport()
    LaunchAndExecTimeDistributionReport()
    StepSuccessesReport()

def set_vars(additional_settings, ordered_vars, settings, param_lists, variables, cfg):
    _settings = dict(settings)
    _variables = copy.deepcopy(variables)
    _ordered_vars = list(ordered_vars)
    for k, v in additional_settings.items():
        _settings[k] = v
        _variables.pop(k, True)
        if k in _ordered_vars:
            _ordered_vars.remove(k)

    _param_lists = [[(key, v) for v in variables[key]] for key in _ordered_vars]

    return _ordered_vars, _settings, _param_lists, _variables, cfg

def set_config(additional_cfg, args):
    cfg = copy.deepcopy(args[-1])
    cfg.d.update(additional_cfg)
    return list(args[:-1]) + [cfg]

def Plot(name, args):
    stats = table_stats.TableStats.stats_by_name[name]
    return dcc.Graph(figure=stats.do_plot(*args)[0])

class TimelineReport():
    def __init__(self):
        self.name = "report: Timeline"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.P("These plots show an overview of the test execution timeline.")]
        header += [html.P("""They are often too dense to be easily interpreted, but by zooming and
panning, they may provide useful information about the events that occured during the test.""")]

        header += [html.H2("Full Timeline")]
        header += [Plot("Timeline", args)]
        header += ["This plot provides information about the timeline of the test Pods execution (in the driver cluster), the steps of the simulated users (ODS prefix) and the Notebook Pods execution."]
        header += html.Br()
        header += html.Br()

        header += [html.H2("Simple Timeline")]
        header += [Plot("Simple Timeline", args)]
        header += ["This plot is based on a Plotly.Express plotting class. It contains almost the same information as the full timeline, but plotted in a simpler way. It may help looking at specific events that the full timeline would group together."]

        return None, header

class PodNodeMappingReport():
    def __init__(self):
        self.name = "report: Pod-Node Mapping"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.P("These plots show an overview of the mapping of the Pods on the different Nodes.")]
        header += [html.P("""The Timeline plots are useful to validate that Pods started and finished on time.""")]
        header += [html.P("""The Distribution plots are useful to visualize how the Pods were scheduled on the different Nodes.""")]

        for what in "Notebooks", "Test Pods":
            header += [html.H1(what)]

            header += [html.H2("Timeline")]
            header += [Plot(f"Pod/Node timeline: {what}", args)]
            header += [html.P(f"This plot shows the timeline of {what} mapping on the cluster's nodes. It can help understanding when the Pods started and finished their execution, as well as which users ran on the same node.")]
            header += html.Br()
            header += html.Br()

            header += [html.H2("Distribution")]
            header += [Plot(f"Pod/Node distribution: {what}", args)]
            header += [f"This plot shows the distribution of the {what} on the cluster's nodes. It provides the Node's name and machine-instance type."]

        return None, header

class UserExecutionOverviewReport():
    def __init__(self):
        self.name = "report: User Execution Overview"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.H2("Execution Time of the User Steps")]
        header += [Plot("Notebook spawn time", args)]
        header += ["This plot shows the time the simulated user took to execute each of the test steps. User IDs shown in bold font failed to pass the test. Failed steps are not shown."]
        header += html.Br()
        header += html.Br()

        header += [html.H2("Execution Time with the failed steps")]
        header += [Plot(f"Notebook spawn time", set_config({"keep_failed_steps": True}, args))]
        header += ["This plot shows the time the simulated user took to execute each of the test steps. User IDs shown in bold font failed to pass the test. Failed steps _are_ shown."]

        header += [html.H2("Execution Time without the failed users")]
        header += [Plot(f"Notebook spawn time", set_config({"hide_failed_users": True}, args))]
        header += ["This plot shows the time the simulated user took to execute each of the test steps. User who failed the test are _not_ shown.."]

        return None, header

class PriceOverviewReport():
    def __init__(self):
        self.name = "Price overview"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        timeline = table_stats.TableStats.stats_by_name['Price to completion']
        if "notebook_size" in ordered_vars:
            ordered_vars.remove("notebook_size")

        report = []
        for notebook_size in variables.get("notebook_size", [settings["notebook_size"]]):
            additional_settings = dict(
                notebook_size=notebook_size
            )
            report += [html.H2(f"Price for size={notebook_size}")]

            report += [dcc.Graph(figure=timeline.do_plot(*set_vars(additional_settings, *args))[0])]


        return None, report

class LaunchAndExecTimeDistributionReport():
    def __init__(self):
        self.name = "report: Launch Time and Execution Time Distribution"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.P("These plots show the distribution of the user steps execution time and launch time.")]

        header += [html.H2("Execution time distribution")]
        header += [Plot("Execution time distribution", args)]
        header += ["This plot provides information about the execution timelength for the different user steps. The failed steps are not taken into account."]
        header += html.Br()
        header += html.Br()

        header += [html.H2("Start time distribution")]
        header += [Plot("Launch time distribution", args)]
        header += ["This plot provides information the start time of the different user steps. The failed steps are not taken into account."]
        header += html.Br()
        header += html.Br()

        return None, header

class StepSuccessesReport():
    def __init__(self):
        self.name = "report: Step Successes"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []

        header += [html.H2("Step Successes")]
        header += [Plot("Step successes", args)]
        header += ["This plot shows the number of users who passed or failed each of the steps."]
        header += html.Br()
        header += html.Br()

        return None, header
