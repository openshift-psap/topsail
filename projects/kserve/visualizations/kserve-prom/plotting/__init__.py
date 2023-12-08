from ..store import prom
from . import prom_report
from . import lts

def register():
    report.register()
    prom.register()
    prom_report.register()
    lts.register()
