import projects.matrix_benchmarking.visualizations.helpers.store.prom as helpers_store_prom
import projects
llmd = getattr(projects, "llm-d")

def register():
    """
    Register Prometheus metrics plots for LLM-D inference visualization
    """
    get_llmd_main_metrics = llmd.visualizations.llmd_inference.store.parsers.get_llmd_main_metrics
    get_llmd_main_metrics(register=True)
