from . import error_report
from . import report
from . import latency
from . import errors
from . import throughput
from . import lts
from . import power

import projects.matrix_benchmarking.visualizations.helpers.plotting.lts_documentation as lts_documentation
import projects.matrix_benchmarking.visualizations.helpers.plotting.kpi_table as kpi_table
import projects.matrix_benchmarking.visualizations.helpers.plotting.kpi_plot as kpi_plot

def register():
    error_report.register()
    report.register()
    latency.register()
    errors.register()
    throughput.register()
    lts.register()
    lts_documentation.register()
    kpi_table.register()
    kpi_plot.register()
    power.register()
