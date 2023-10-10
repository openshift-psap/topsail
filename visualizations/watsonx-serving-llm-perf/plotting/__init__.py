from . import error_report
from . import report
from . import latency

def register():
    error_report.register()
    report.register()
    latency.register()
