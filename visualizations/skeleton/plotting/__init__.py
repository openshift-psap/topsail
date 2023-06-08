from . import error_report
from ..store import prom
from . import prom_report

def register():
    error_report.register()
    report.register()
    prom.register()
    prom_report.register()
