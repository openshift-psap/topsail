from ..store import prom
from . import prom_report
from . import prom_summary
import projects.matrix_benchmarking.visualizations.helpers.plotting.lts_documentation as lts_documentation
import projects.matrix_benchmarking.visualizations.helpers.plotting.kpi_table as kpi_table

def register():
    prom.register()
    prom_report.register()
    lts_documentation.register()
    prom_summary.register()
    kpi_table.register()
