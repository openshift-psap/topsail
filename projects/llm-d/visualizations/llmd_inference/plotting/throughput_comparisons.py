from dash import html

import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    ThroughputComparisonsReport()

def _generate_throughput_plots(args):
    """
    Generate throughput plots with the given configuration

    Args:
        args: Plot arguments (potentially filtered for specific model/load_shape)

    Returns:
        List of HTML elements containing the plots and descriptions
    """
    content = []

    content.append(html.H4("🚀 Token Throughput vs Concurrency"))
    content.append(html.P([
        "Token generation throughput scaling analysis."
    ]))
    content += report.Plot_and_Text("Guidellm Tokens vs Concurrency", args)

    # content.append(html.H4("🚀 Token Throughput Percentiles vs Concurrency"))
    # content.append(html.P([
    #     "Performance consistency analysis showing percentile distributions."
    # ]))
    # content += report.Plot_and_Text("Token Throughput Percentiles Analysis", args)

    content.append(html.Hr())

    return content

class ThroughputComparisonsReport():
    def __init__(self):
        self.name = "report: Throughput Comparisons"
        self.id_name = self.name.lower().replace(" ", "_").replace("-", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, *args):
        """
        Generate throughput comparison report combining token throughput plots
        """

        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []
        header.append(html.H2("🚀 Throughput Comparisons"))
        header.append(html.Br())

        header.append(html.P([
            "This report provides comprehensive analysis of token throughput performance ",
            "organized by model and load shape to enable focused comparisons."
        ]))
        header.append(html.Br())


        def filter_flavors(setting_lists, flavor_filter):
            """Filter flavors from setting_lists based on provided filter function"""
            updated_setting_lists = []
            for setting_list in setting_lists:
                if setting_list and setting_list[0][0] == 'flavor':
                    # Apply the filter function to flavors
                    filtered_flavors = [(k, v) for k, v in setting_list if flavor_filter(v)]
                    if filtered_flavors:
                        updated_setting_lists.append(filtered_flavors)
                else:
                    updated_setting_lists.append(setting_list)
            setting_lists[:] = updated_setting_lists


        # Intelligent Routing Section
        header.append(html.H2("🧠 Intelligent Routing"))
        header.append(html.P([
            "Analysis of intelligent routing performance using llama3.3-70b model, ",
            "comparing routing-enabled configurations across different load shapes."
        ]))

        for with_simple in False, True:
            if with_simple:
                header.append(html.H2("Intelligent Routing VS native"))
            else:
                header.append(html.H2("Intelligent Routing"))


            for load_shape in variables['load_shape']:
                header.append(html.H3(f"📊 Load Shape: {load_shape}"))

                # Set llama3.3-70b and remove simple flavor
                ir_settings = {"model": "llama3.3-70b", "load_shape": load_shape}
                ir_args = report.set_settings(ir_settings, args)

                # Filter out simple flavor from the remaining args if it exists
                ordered_vars, settings, setting_lists, variables_filtered, cfg = ir_args

                def include_flavor(v):
                    if v.startswith('pd-'): return False
                    if not with_simple and v.startswith("simple"): return False
                    if v.startswith("simple") and not v.endswith("tp2-x4"): return False

                    return True

                # Remove simple and pd- flavors
                filter_flavors(
                    setting_lists,
                    include_flavor,
                )
                ir_args_final = (ordered_vars, settings, setting_lists, variables_filtered, cfg)

                header += _generate_throughput_plots(ir_args_final)

        header.append(html.Hr())

        # P/D Disaggregation Section
        header.append(html.H2("🔄 P/D Disaggregation"))
        header.append(html.P([
            "Prefill/Decode disaggregation analysis using gpt-oss-120b model, ",
            "comparing disaggregated configurations across different load shapes."
        ]))

        if 'model' in variables and 'gpt-oss-120b' in variables['model'] and 'load_shape' in variables:
            for load_shape in variables['load_shape']:
                header.append(html.H3(f"📊 Load Shape: {load_shape}"))

                # Set gpt-oss-120b model
                pd_settings = {"model": "gpt-oss-120b", "load_shape": load_shape}
                pd_args = report.set_settings(pd_settings, args)

                # Filter to show only pd- flavors
                ordered_vars, settings, setting_lists, variables_filtered, cfg = pd_args
                filter_flavors(setting_lists, lambda v: (v.startswith('pd-') or v.endswith('-tp4-x4')) and "(eth)" not in v)
                pd_args_final = (ordered_vars, settings, setting_lists, variables_filtered, cfg)

                header += _generate_throughput_plots(pd_args_final)

        header.append(html.Hr())

        # Baseline Section
        header.append(html.H2("📊 Baseline"))
        header.append(html.P([
            "Baseline performance analysis using simple flavor configuration, ",
            "comparing across different models and load shapes."
        ]))

        if 'model' in variables and 'llama3.3-70b' in variables['model'] and 'load_shape' in variables:
            for load_shape in variables['load_shape']:
                # Skip multiturn load shape for baseline
                if load_shape == 'Multiturn':
                    continue

                header.append(html.H3(f"📊 Load Shape: {load_shape}"))

                # Set llama3.3-70b model
                baseline_settings = {"model": "llama3.3-70b", "load_shape": load_shape}
                baseline_args = report.set_settings(baseline_settings, args)

                # Filter to show only simple flavors
                ordered_vars, settings, setting_lists, variables_filtered, cfg = baseline_args
                filter_flavors(setting_lists, lambda v: v.startswith('simple'))
                baseline_args_final = (ordered_vars, settings, setting_lists, variables_filtered, cfg)

                header += _generate_throughput_plots(baseline_args_final)

        # Add overall insights
        header.append(html.H3("💡 Key Insights"))
        header.append(html.Ul([
            html.Li("Compare throughput scaling patterns between models"),
            html.Li("Analyze how load shapes affect performance characteristics"),
            html.Li("Identify optimal concurrency levels for each model-load combination"),
            html.Li("Evaluate performance consistency using percentile distributions"),
            html.Li("Compare trade-offs between different configurations within each scenario"),
        ]))

        return None, header
