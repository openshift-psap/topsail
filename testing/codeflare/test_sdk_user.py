import prepare_sdk_user

def test(name=None, dry_mode=None, visualize=None, capture_prom=None):
    """
    Runs the test from the CI

    Args:
      name: name of the test to run. If empty, run all the tests of the configuration file
      dry_mode: if True, do not execute the tests, only list what would be executed
      visualize: if False, do not generate the visualization reports
      capture_prom: if False, do not capture Prometheus database
    """
    
    test.apply_prefer_pr()
    pass
