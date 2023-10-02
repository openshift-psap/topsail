from ..store import prom
from . import prom_report

def register():
    report.register()
    prom.register()
    prom_report.register()
