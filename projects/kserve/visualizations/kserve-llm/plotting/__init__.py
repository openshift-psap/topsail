from . import error_report
from . import report
from . import latency
from . import errors
from . import throughput
from . import lts

def register():
    error_report.register()
    report.register()
    latency.register()
    errors.register()
    throughput.register()
    lts.register()
