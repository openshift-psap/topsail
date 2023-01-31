from .. import store_prom

def register():
    store_prom.get_test_metrics(register=True)
