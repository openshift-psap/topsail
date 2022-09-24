from collections import defaultdict

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

from . import prom
from . import completion
from . import report
from . import mapping
from . import spawntime
from . import status
from . import launch_time
from . import error_report
from . import prom_report
from . import notebook_performance

def register():
    prom.register()
    completion.register()
    report.register()
    mapping.register()
    spawntime.register()
    status.register()
    launch_time.register()
    error_report.register()
    prom_report.register()
    notebook_performance.register()
