from dash import html, dcc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import copy

import projects.matrix_benchmarking.visualizations.helpers.plotting.report as report

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    BaselineComparisonsReport()
    IntelligentRoutingComparisonsReport()
    PDComparisonsReport()

def _generate_ttft_percentiles_plot(args):
    """Generate TTFT percentiles plot in single chart"""
    ordered_vars, settings, setting_lists, variables, cfg = args
    entries = list(common.Matrix.all_records(settings, setting_lists))

    # Generate DataFrame
    data = []
    for entry in entries:
        if not entry.results.guidellm_benchmarks:
            continue

        entry_name = entry.get_name(variables)
        platform = getattr(entry.settings, 'platform', 'unknown')

        for benchmark in entry.results.guidellm_benchmarks:
            if benchmark.strategy == "throughput":
                continue


            # Use available TTFT fields with fallbacks for missing percentiles
            ttft_p50 = getattr(benchmark, 'ttft_p50', getattr(benchmark, 'ttft_median', None))
            ttft_p90 = getattr(benchmark, 'ttft_p90', getattr(benchmark, 'ttft_p95', None))

            data.append({
                'Test Configuration': entry_name,
                'Platform': platform,
                'Concurrency': benchmark.request_concurrency,
                'Strategy': benchmark.strategy,
                'TTFT P10': getattr(benchmark, 'ttft_p10', None),
                'TTFT P25': getattr(benchmark, 'ttft_p25', None),
                'TTFT P50': ttft_p50,
                'TTFT P75': getattr(benchmark, 'ttft_p75', None),
                'TTFT P90': ttft_p90,
            })

    if not data:
        return html.P("No TTFT data available")

    df = pd.DataFrame(data)
    df = df.sort_values(['Concurrency', "Test Configuration"])


    # Create plot - use same color assignment as px.line()
    fig = go.Figure()
    configurations = sorted(df['Test Configuration'].unique())

    # Create a dummy px.line figure to get the same color assignment
    dummy_df = pd.DataFrame({'Test Configuration': configurations, 'x': range(len(configurations)), 'y': range(len(configurations))})
    dummy_fig = px.line(dummy_df, x='x', y='y', color='Test Configuration')
    color_map = {}
    for trace in dummy_fig.data:
        config_name = trace.name
        color_map[config_name] = trace.line.color

    percentiles_config = [
        {'percentile': 'P10', 'line_style': {'width': 2, 'dash': 'longdash'}, 'opacity': 0.6},
        {'percentile': 'P25', 'line_style': {'width': 2, 'dash': 'dot'}, 'opacity': 0.7},
        {'percentile': 'P50', 'line_style': {'width': 4, 'dash': 'solid'}, 'opacity': 1.0},
        {'percentile': 'P75', 'line_style': {'width': 3, 'dash': 'dash'}, 'opacity': 0.9},
        {'percentile': 'P90', 'line_style': {'width': 2, 'dash': 'dashdot'}, 'opacity': 0.8},
    ]

    for config_name in configurations:
        config_df = df[df['Test Configuration'] == config_name].sort_values('Concurrency')
        if len(config_df) == 0:
            continue

        for perc_config in percentiles_config:
            percentile = perc_config['percentile']
            column_name = f'TTFT {percentile}'

            # Skip if column doesn't exist or all values are None/NaN
            if (column_name not in config_df.columns or
                config_df[column_name].isna().all() or
                config_df[column_name].isnull().all()):
                continue

            trace_name = f'{config_name} - {percentile}'
            base_color = color_map.get(config_name, px.colors.qualitative.Set1[0])

            fig.add_trace(go.Scatter(
                x=config_df['Concurrency'],
                y=config_df[column_name],
                mode='lines+markers',
                name=trace_name,
                legendgroup=f'{config_name}',
                marker=dict(size=6),
                line=dict(color=base_color, **perc_config['line_style']),
                opacity=perc_config['opacity'],
                hovertemplate=f'<b>{config_name}</b><br>TTFT {percentile}<br>Concurrency: %{{x}}<br>Value: %{{y:.1f}} ms<br><extra></extra>',
                showlegend=True
            ))

    fig.update_layout(
        title="TTFT Percentiles vs Concurrency<br><sub>Lower is better • P10 (long dash), P25 (dotted), P50 (solid), P75 (dashed), P90 (dash-dot)</sub>",
        showlegend=True,
        hovermode='closest',
        height=600,
        xaxis_title="Concurrency",
        yaxis_title="TTFT (ms)",
    )
    fig.update_yaxes(rangemode="tozero")

    return dcc.Graph(figure=fig)


def _generate_itl_percentiles_plot(args):
    """Generate ITL percentiles plot in single chart"""
    ordered_vars, settings, setting_lists, variables, cfg = args
    entries = list(common.Matrix.all_records(settings, setting_lists))

    # Generate DataFrame
    data = []
    for entry in entries:
        if not entry.results.guidellm_benchmarks:
            continue

        entry_name = entry.get_name(variables)
        platform = getattr(entry.settings, 'platform', 'unknown')

        for benchmark in entry.results.guidellm_benchmarks:
            if benchmark.strategy == "throughput":
                continue


            # Use available ITL fields with fallbacks for missing percentiles
            itl_p50 = getattr(benchmark, 'itl_p50', getattr(benchmark, 'itl_median', None))
            itl_p90 = getattr(benchmark, 'itl_p90', getattr(benchmark, 'itl_p95', None))

            data.append({
                'Test Configuration': entry_name,
                'Platform': platform,
                'Concurrency': benchmark.request_concurrency,
                'Strategy': benchmark.strategy,
                'ITL P10': getattr(benchmark, 'itl_p10', None),
                'ITL P25': getattr(benchmark, 'itl_p25', None),
                'ITL P50': itl_p50,
                'ITL P75': getattr(benchmark, 'itl_p75', None),
                'ITL P90': itl_p90,
            })

    if not data:
        return html.P("No ITL data available")

    df = pd.DataFrame(data)
    df = df.sort_values(['Concurrency', "Test Configuration"])

    # Convert from seconds to milliseconds
    for col in ['ITL P10', 'ITL P25', 'ITL P50', 'ITL P75', 'ITL P90']:
        if col in df.columns:
            df[col] = df[col] * 1000  # Convert to ms


    # Create plot - use same color assignment as px.line()
    fig = go.Figure()
    configurations = sorted(df['Test Configuration'].unique())

    # Create a dummy px.line figure to get the same color assignment
    dummy_df = pd.DataFrame({'Test Configuration': configurations, 'x': range(len(configurations)), 'y': range(len(configurations))})
    dummy_fig = px.line(dummy_df, x='x', y='y', color='Test Configuration')
    color_map = {}
    for trace in dummy_fig.data:
        config_name = trace.name
        color_map[config_name] = trace.line.color

    percentiles_config = [
        {'percentile': 'P10', 'line_style': {'width': 2, 'dash': 'longdash'}, 'opacity': 0.6},
        {'percentile': 'P25', 'line_style': {'width': 2, 'dash': 'dot'}, 'opacity': 0.7},
        {'percentile': 'P50', 'line_style': {'width': 4, 'dash': 'solid'}, 'opacity': 1.0},
        {'percentile': 'P75', 'line_style': {'width': 3, 'dash': 'dash'}, 'opacity': 0.9},
        {'percentile': 'P90', 'line_style': {'width': 2, 'dash': 'dashdot'}, 'opacity': 0.8},
    ]

    for config_name in configurations:
        config_df = df[df['Test Configuration'] == config_name].sort_values('Concurrency')
        if len(config_df) == 0:
            continue

        for perc_config in percentiles_config:
            percentile = perc_config['percentile']
            column_name = f'ITL {percentile}'

            # Skip if column doesn't exist or all values are None/NaN
            if (column_name not in config_df.columns or
                config_df[column_name].isna().all() or
                config_df[column_name].isnull().all()):
                continue

            trace_name = f'{config_name} - {percentile}'
            base_color = color_map.get(config_name, px.colors.qualitative.Set1[0])

            fig.add_trace(go.Scatter(
                x=config_df['Concurrency'],
                y=config_df[column_name],
                mode='lines+markers',
                name=trace_name,
                legendgroup=f'{config_name}',
                marker=dict(size=6),
                line=dict(color=base_color, **perc_config['line_style']),
                opacity=perc_config['opacity'],
                hovertemplate=f'<b>{config_name}</b><br>ITL {percentile}<br>Concurrency: %{{x}}<br>Value: %{{y:.1f}} ms<br><extra></extra>',
                showlegend=True
            ))

    fig.update_layout(
        title="ITL Percentiles vs Concurrency<br><sub>Lower is better • P10 (long dash), P25 (dotted), P50 (solid), P75 (dashed), P90 (dash-dot)</sub>",
        showlegend=True,
        hovermode='closest',
        height=600,
        xaxis_title="Concurrency",
        yaxis_title="ITL (ms)",
    )
    fig.update_yaxes(rangemode="tozero")

    return dcc.Graph(figure=fig)


def _generate_throughput_plots(args):
    """
    Generate throughput plots with five tabs: Throughput (mean), TTFT P50, TTFT Percentiles, ITL P50, ITL Percentiles

    Args:
        args: Plot arguments (potentially filtered for specific model/load_shape)

    Returns:
        List of HTML elements containing the tabbed plots
    """
    # Tab 1: Throughput (Mean)
    throughput_content = []
    throughput_content.append(html.H4("🚀 Token Throughput vs Concurrency (Mean)"))
    throughput_content.append(html.P("Token generation throughput scaling analysis using mean values."))
    throughput_content += report.Plot_and_Text("Guidellm Tokens vs Concurrency", args)

    # Tab 2: TTFT P50
    ttft_p50_content = []
    ttft_p50_content.append(html.H4("⏱️ Time To First Token (P50)"))
    ttft_p50_content.append(html.P("Median time to first token analysis."))
    ttft_p50_content += report.Plot_and_Text("Guidellm TTFT Analysis", args)

    # Tab 3: TTFT Percentiles
    ttft_percentiles_content = []
    ttft_percentiles_content.append(html.H4("📊 TTFT Percentiles"))
    ttft_percentiles_content.append(html.P("Complete TTFT percentile distribution analysis (P10, P25, P50, P75, P90)."))
    ttft_percentiles_content.append(_generate_ttft_percentiles_plot(args))

    # Tab 4: ITL P50
    itl_p50_content = []
    itl_p50_content.append(html.H4("🔄 Inter-Token Latency (P50)"))
    itl_p50_content.append(html.P("Median inter-token latency analysis."))
    itl_p50_content += report.Plot_and_Text("Guidellm ITL Analysis", args)

    # Tab 5: ITL Percentiles
    itl_percentiles_content = []
    itl_percentiles_content.append(html.H4("📊 ITL Percentiles"))
    itl_percentiles_content.append(html.P("Complete ITL percentile distribution analysis (P10, P25, P50, P75, P90)."))
    itl_percentiles_content.append(_generate_itl_percentiles_plot(args))

    # Create tabs
    tabs = dcc.Tabs(id="throughput-tabs", value="throughput", children=[
        dcc.Tab(label="🚀 Throughput", value="throughput", children=[
            html.Div(throughput_content, style={"padding": "20px"})
        ]),
        dcc.Tab(label="⏱️ TTFT P50", value="ttft-p50", children=[
            html.Div(ttft_p50_content, style={"padding": "20px"})
        ]),
        dcc.Tab(label="📊 TTFT Percentiles", value="ttft-percentiles", children=[
            html.Div(ttft_percentiles_content, style={"padding": "20px"})
        ]),
        dcc.Tab(label="🔄 ITL P50", value="itl-p50", children=[
            html.Div(itl_p50_content, style={"padding": "20px"})
        ]),
        dcc.Tab(label="📊 ITL Percentiles", value="itl-percentiles", children=[
            html.Div(itl_percentiles_content, style={"padding": "20px"})
        ]),
    ])

    return [tabs]

class BaselineComparisonsReport():
    def __init__(self):
        self.name = "report: Baseline Comparisons"
        self.id_name = self.name.lower().replace(" ", "_").replace("-", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, *args):
        """
        Generate baseline comparison report for simple flavor configurations
        """

        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []
        header.append(html.H2("📊 Baseline Comparisons"))
        header.append(html.Br())

        header.append(html.P([
            "Baseline performance analysis using simple flavor configuration, ",
            "comparing across different models and load shapes."
        ]))
        header.append(html.Br())

        args = report.set_config(dict(markers_by="platform"), args)

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

        # Get simple flavors
        simple_flavors = [f for f in common.Matrix.settings.get('flavor', []) if f.startswith('simple')]

        for load_shape in common.Matrix.settings.get('load_shape', []):
            # Skip multiturn load shape for baseline
            if load_shape == 'Multiturn':
                continue

            header.append(html.H3(f"📊 Load Shape: {load_shape}"))

            for flavor in simple_flavors:
                header.append(html.H4(f"🔧 {flavor}"))
                if flavor == "simple-tp4-x4":
                    header.append(html.I(f"Skipped, not relevant for baseline."))
                    continue

                # Set llama3.3-70b model and specific simple flavor
                baseline_settings = {"model": "llama3.3-70b", "load_shape": load_shape, "flavor": flavor}
                baseline_args = report.set_settings(baseline_settings, args)

                header += _generate_throughput_plots(baseline_args)

        return None, header


class IntelligentRoutingComparisonsReport():
    def __init__(self):
        self.name = "report: Intelligent-routing Comparisons"
        self.id_name = self.name.lower().replace(" ", "_").replace("-", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, *args):
        """
        Generate intelligent routing comparison report
        """

        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []
        header.append(html.H2("🧠 Intelligent Routing Comparisons"))
        header.append(html.Br())

        header.append(html.P([
            "Analysis of intelligent routing performance using llama3.3-70b model, ",
            "comparing routing-enabled configurations across different load shapes."
        ]))
        header.append(html.Br())

        args = report.set_config(dict(markers_by="platform"), args)

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

        for with_simple in False, True:
            if with_simple:
                header.append(html.H2("Intelligent Routing VS native"))
            else:
                header.append(html.H2("Intelligent Routing"))

            for load_shape in common.Matrix.settings.get('load_shape', []):
                header.append(html.H3(f"📊 Load Shape: {load_shape}"))

                # Set llama3.3-70b and remove simple flavor
                ir_settings = {"model": "llama3.3-70b", "load_shape": load_shape}
                ir_args = report.set_settings(ir_settings, args)

                # Filter out simple flavor from the remaining args if it exists
                ordered_vars, settings, setting_lists, variables_filtered, cfg = ir_args

                def include_ir_flavor(v):
                    if v.startswith('pd-'): return False
                    if not with_simple and v.startswith("simple"): return False
                    if v.startswith("simple") and not v.endswith("tp2-x4"): return False

                    return True

                # Remove simple and pd- flavors
                filter_flavors(setting_lists, include_ir_flavor)
                ir_args_final = (ordered_vars, settings, setting_lists, variables_filtered, cfg)

                header += _generate_throughput_plots(ir_args_final)

        return None, header


class PDComparisonsReport():
    def __init__(self):
        self.name = "report: P-D Comparisons"
        self.id_name = self.name.lower().replace(" ", "_").replace("-", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, *args):
        """
        Generate P/D disaggregation comparison report
        """

        ordered_vars, settings, setting_lists, variables, cfg = args

        header = []
        header.append(html.H2("🔄 P/D Disaggregation Comparisons"))
        header.append(html.Br())

        header.append(html.P([
            "Prefill/Decode disaggregation analysis using gpt-oss-120b model, ",
            "comparing disaggregated configurations across different load shapes."
        ]))
        header.append(html.Br())

        args = report.set_config(dict(markers_by="platform"), args)

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

        for load_shape in common.Matrix.settings.get('load_shape', []):
            header.append(html.H3(f"📊 Load Shape: {load_shape}"))

            # Set gpt-oss-120b model
            pd_settings = {"model": "gpt-oss-120b", "load_shape": load_shape}
            pd_args = report.set_settings(pd_settings, args)

            # Filter to show only pd- flavors
            ordered_vars, settings, setting_lists, variables_filtered, cfg = pd_args

            def include_pd_flavor(v):
                if "(eth)" in v: return False
                #if "(sched v4)" in v: return False
                if not (v.startswith('pd-') or v.endswith('-tp4-x4')): return False
                return True

            filter_flavors(setting_lists, include_pd_flavor)
            pd_args_final = (ordered_vars, settings, setting_lists, variables_filtered, cfg)

            header += _generate_throughput_plots(pd_args_final)

        return None, header
