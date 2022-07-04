from collections import defaultdict

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

from . import simple_timeline
from . import advanced_timeline
from . import prom
from . import completion
from . import report
from . import mapping
from . import spawntime
from . import  status

def register():
    simple_timeline.register()
    advanced_timeline.register()
    prom.register()
    completion.register()
    report.register()
    mapping.register()
    spawntime.register()
    status.register()
