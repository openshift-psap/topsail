from . import error_report
from . import sfttrainer
import projects.matrix_benchmarking.visualizations.helpers.plotting.lts_documentation as lts_documentation

def register():
    error_report.register()
    report.register()
    lts_documentation.register()
    sfttrainer.register()
