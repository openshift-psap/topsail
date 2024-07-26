from . import quality_report
from . import quality

def register():
    quality_report.register()
    quality.register()
