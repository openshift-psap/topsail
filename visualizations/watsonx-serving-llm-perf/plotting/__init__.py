from . import error_report
from . import report
from . import latency
from . import errors

def register():
    error_report.register()
    report.register()
    latency.register()
    errors.register()
