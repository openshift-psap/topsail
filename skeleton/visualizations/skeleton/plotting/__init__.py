from . import error_report
from ..store import prom
from . import prom_report
from . import report

import projects.matrix_benchmarking.visualizations.helpers.plotting.lts_documentation as lts_documentation
import projects.matrix_benchmarking.visualizations.helpers.plotting.kpi_table as kpi_table
import projects.matrix_benchmarking.visualizations.helpers.plotting.kpi_plot as kpi_plot

def register():
    error_report.register()
    report.register()
    prom.register()
    prom_report.register()
    lts_documentation.register()
    kpi_table.register()
    kpi_plot.register()
