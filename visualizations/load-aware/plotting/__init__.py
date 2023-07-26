from . import error_report
from ..store import prom
from . import prom_report
from . import pod_times
from . import scheduler_report
from . import mapping
from . import comparison

def register():
    error_report.register()
    report.register()
    prom.register()
    prom_report.register()
    pod_times.register()
    scheduler_report.register()
    mapping.register()
    comparison.register()
