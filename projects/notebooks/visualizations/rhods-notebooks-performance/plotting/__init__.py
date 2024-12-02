from . import report
from . import notebook_performance_comparison
from . import notebook_performance

import projects.matrix_benchmarking.visualizations.helpers.plotting.lts_documentation as lts_documentation
import projects.matrix_benchmarking.visualizations.helpers.plotting.kpi_table as kpi_table

def register():
    report.register()
    notebook_performance_comparison.register()
    notebook_performance.register()
    lts_documentation.register()
    kpi_table.register()
