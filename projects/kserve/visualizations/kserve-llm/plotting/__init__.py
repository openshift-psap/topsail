from . import error_report
from . import report
from . import latency
from . import errors
from . import throughput
from . import lts

import projects.matrix_benchmarking.visualizations.helpers.plotting.lts_documentation as lts_documentation
import projects.matrix_benchmarking.visualizations.helpers.plotting.kpi_table as kpi_table

def register():
    error_report.register()
    report.register()
    latency.register()
    errors.register()
    throughput.register()
    lts.register()
    lts_documentation.register()
    kpi_table.register()
