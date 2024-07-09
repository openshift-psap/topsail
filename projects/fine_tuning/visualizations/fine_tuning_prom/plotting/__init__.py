from ..store import prom
from . import prom_report
from . import lts_documentation
from . import prom_summary

def register():
    report.register()
    prom.register()
    prom_report.register()
    lts_documentation.register()
    prom_summary.register()
