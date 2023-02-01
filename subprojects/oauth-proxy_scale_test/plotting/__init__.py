from .. import store_prom
from . import visu

def register():
    store_prom.get_test_metrics(register=True)
    visu.Visualize()
