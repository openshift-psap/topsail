# Register all plotting modules
def register():
    """Register all plotting functions with matrix benchmarking framework"""

    # Import and register each module
    from . import report
    from . import error_report
    from . import throughput_analysis

    report.register()
    error_report.register()
    throughput_analysis.register()
