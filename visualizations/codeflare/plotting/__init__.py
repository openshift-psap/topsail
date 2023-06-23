from . import error_report
from ..store import prom
from . import prom_report
from . import resource_allocation

def register():
    error_report.register()
    report.register()
    prom.register()
    prom_report.register()
    resource_allocation.register()
