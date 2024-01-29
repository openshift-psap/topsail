from . import report
from . import notebook_performance_comparison
from . import gating_report
from . import notebook_performance
from . import lts_documentation
from . import lts_kpis

def register():
    report.register()
    notebook_performance_comparison.register()
    gating_report.register()
    notebook_performance.register()
    lts_documentation.register()
    lts_kpis.register()
