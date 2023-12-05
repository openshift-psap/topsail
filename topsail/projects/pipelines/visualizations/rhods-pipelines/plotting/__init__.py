from . import error_report
from . import spawntime
from . import report
from . import status
from ..store import prom
from . import prom_report
from . import perf_report
from . import mapping

def register():
    error_report.register()
    spawntime.register()
    report.register()
    prom.register()
    prom_report.register()
    perf_report.register()
    mapping.register()
