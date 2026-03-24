import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common


def _get_plot_title_with_load_shape(base_title, variables, settings):
    """
    Helper function to add load_shape info to plot titles if not in variables

    Args:
        base_title: The base title/subtitle (e.g., "Token Throughput vs Concurrency<br><sub>Higher is better</sub>")
        variables: Dict of variables being varied in the test
        settings: Test settings object

    Returns:
        Updated title with load_shape appended if needed
    """
    if "load_shape" not in variables:
        load_shape = getattr(settings, 'load_shape', None)
        if load_shape:
            # Insert load_shape info before the closing </sub> tag or at the end
            if "<br><sub>" in base_title and "</sub>" in base_title:
                # Insert before closing </sub>
                return base_title.replace("</sub>", f" • Load Shape: {load_shape}</sub>")
            else:
                # Append as subtitle
                return f"{base_title}<br><sub>Load Shape: {load_shape}</sub>"
    return base_title


def register():
    GuidellmThroughputScaling()
    GuidellmLatencyVsThroughput()
    GuidellmLatencyOverview()
    GuidellmTokensConcurrency()
    GuidellmTTFTAnalysis()
    GuidellmTPOTAnalysis()
    GuidellmITLAnalysis()
    GuidellmE2ELatencyAnalysis()

    TokenThroughputAnalysis()

class GuidellmThroughputScaling():
    def __init__(self):
        self.name = "Guidellm Throughput Scaling"
        self.id_name = "guidellm_throughput_scaling"
        self.no_graph = False
        self.is_report = False

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        """
        Plot request rate vs concurrency to show scaling behavior
        """
        ## rewrite below
        entries = list(common.Matrix.all_records(settings, setting_lists))

        # 1. Generate DataFrame
        data = []
        for entry in entries:
            if not entry.results.guidellm_benchmarks:
                continue

            # Get unique name for this entry (includes flavor info)
            entry_name = entry.get_name(variables)

            # Include all strategies - let's show the full picture
            for benchmark in entry.results.guidellm_benchmarks:
                if benchmark.strategy == "throughput":
                    continue

                # Determine strategy type for better grouping
                strategy_type = "Other"
                if 'constant' in benchmark.strategy.lower():
                    if 'arrival_rate' in benchmark.strategy.lower():
                        strategy_type = "Constant Arrival Rate"
                    elif 'concurrency' in benchmark.strategy.lower():
                        strategy_type = "Constant Concurrency"
                    else:
                        strategy_type = "Constant"
                elif 'sweep' in benchmark.strategy.lower():
                    strategy_type = "Sweep"
                elif 'ramp' in benchmark.strategy.lower():
                    strategy_type = "Ramp"

                data.append({
                    'Test Configuration': entry_name,
                    'Concurrency': benchmark.request_concurrency,
                    'Request Rate (req/s)': benchmark.request_rate,
                    'Strategy': benchmark.strategy,
                    'Strategy Type': strategy_type,
                    'TTFT (ms)': benchmark.ttft_median,
                    'Latency (ms)': benchmark.request_latency_median * 1000,
                    'Tokens/s': benchmark.tokens_per_second
                })

        if not data:
            return None, ["No Guidellm benchmark data available"]

        df = pd.DataFrame(data)

        # Sort by Concurrency for proper plot ordering
        df = df.sort_values('Concurrency')

        # 2. Generate plotly express plot
        title = _get_plot_title_with_load_shape(
            'Request Throughput vs Concurrency by Configuration',
            variables,
            settings
        )

        fig = px.scatter(df,
                        hover_data=df.columns,
                        x='Concurrency',
                        y='Request Rate (req/s)',
                        color='Test Configuration',
                        symbol='Strategy Type',
                        size='Tokens/s',
                        text='Strategy',
                        title=title)

        fig.update_traces(textposition="top center")
        fig.update_layout(showlegend=True)

        # Add trend lines for constant strategies
        constant_data = df[df['Strategy Type'].str.contains('Constant', na=False)]
        if len(constant_data) > 1:
            fig.add_scatter(x=constant_data['Concurrency'],
                           y=constant_data['Request Rate (req/s)'],
                           mode='lines',
                           name='Constant Strategy Trend',
                           line=dict(dash='dash', color='gray'),
                           showlegend=True)

        # 3. Generate summary text
        max_rate = df['Request Rate (req/s)'].max()
        min_rate = df['Request Rate (req/s)'].min()
        avg_rate = df['Request Rate (req/s)'].mean()

        best_strategy = df.loc[df['Request Rate (req/s)'].idxmax()]

        # Configuration breakdown
        config_counts = df['Test Configuration'].value_counts()
        strategy_counts = df['Strategy Type'].value_counts()
        total_strategies = len(df)

        performance_ratio = ((max_rate - min_rate) / min_rate * 100) if min_rate > 0 else 0

        msg = []
        msg.append(f"Showing {total_strategies} strategies across {len(config_counts)} test configurations:")
        msg.append(html.Br())
        for config, count in config_counts.items():
            msg.append(f"• {config}: {count} strategies")
            msg.append(html.Br())
        msg.append(html.Br())
        msg.append(f"Strategy types: {', '.join(strategy_counts.keys())}")
        msg.append(html.Br())
        msg.append(html.Br())
        msg.append(f"Best performing: {best_strategy['Strategy']} in {best_strategy['Test Configuration']} ({max_rate:.2f} req/s)")
        msg.append(html.Br())
        msg.append(f"Performance range: {min_rate:.2f} - {max_rate:.2f} req/s ({performance_ratio:.1f}% spread)")
        msg.append(html.Br())
        msg.append("Note: Bubble size shows token throughput, color shows test configuration, shape shows strategy type")

        # 4. Return fig, msg
        return fig, msg


class GuidellmLatencyVsThroughput():
    def __init__(self):
        self.name = "Guidellm Latency vs Throughput"
        self.id_name = "guidellm_latency_vs_throughput"
        self.no_graph = False
        self.is_report = False

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        """
        Plot latency vs throughput trade-off
        """
        ## rewrite below
        entries = list(common.Matrix.all_records(settings, setting_lists))

        # 1. Generate DataFrame
        data = []
        for entry in entries:
            if not entry.results.guidellm_benchmarks:
                continue

            # Get unique name for this entry (includes flavor info)
            entry_name = entry.get_name(variables)

            for benchmark in entry.results.guidellm_benchmarks:
                if benchmark.strategy == "throughput":
                    continue

                data.append({
                    'Test Configuration': entry_name,
                    'Request Rate (req/s)': benchmark.request_rate,
                    'Latency (ms)': benchmark.request_latency_median * 1000,  # Convert to ms
                    'Strategy': benchmark.strategy,
                    'TTFT (ms)': benchmark.ttft_median,
                    'Concurrency': benchmark.request_concurrency,
                    'Tokens/s': benchmark.tokens_per_second
                })

        if not data:
            return None, ["No Guidellm benchmark data available"]

        df = pd.DataFrame(data)

        # Sort by Concurrency for consistent ordering
        df = df.sort_values('Concurrency')

        # 2. Generate plotly express plot
        title = _get_plot_title_with_load_shape(
            'Latency vs Throughput Trade-off by Configuration',
            variables,
            settings
        )

        fig = px.scatter(df,
                        hover_data=df.columns,
                        x='Request Rate (req/s)',
                        y='Latency (ms)',
                        color='Test Configuration',
                        symbol='Test Configuration',
                        size='Tokens/s',
                        text='Strategy',
                        title=title)

        fig.update_traces(textposition="top center")
        fig.update_layout(showlegend=True)

        # 3. Generate summary text
        best_throughput = df.loc[df['Request Rate (req/s)'].idxmax()]
        best_latency = df.loc[df['Latency (ms)'].idxmin()]

        # Calculate efficiency (high throughput, low latency)
        df['Efficiency'] = df['Request Rate (req/s)'] / df['Latency (ms)']
        most_efficient = df.loc[df['Efficiency'].idxmax()]

        msg = []
        msg.append(f"Highest throughput: {best_throughput['Strategy']} in {best_throughput['Test Configuration']} ({best_throughput['Request Rate (req/s)']:.2f} req/s)")
        msg.append(html.Br())
        msg.append(f"Lowest latency: {best_latency['Strategy']} in {best_latency['Test Configuration']} ({best_latency['Latency (ms)']:.1f} ms)")
        msg.append(html.Br())
        msg.append(f"Most efficient: {most_efficient['Strategy']} in {most_efficient['Test Configuration']} ({most_efficient['Efficiency']:.2f} req/s per ms)")
        msg.append(html.Br())
        msg.append("Note: Higher throughput and lower latency indicate better performance")

        # 4. Return fig, msg
        return fig, msg

class GuidellmLatencyOverview():
    def __init__(self):
        self.name = "Guidellm Latency Overview"
        self.id_name = "guidellm_latency_overview"
        self.no_graph = False
        self.is_report = False

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        """
        Performance overview focusing on latency metrics across strategies
        """
        ## rewrite below
        entries = list(common.Matrix.all_records(settings, setting_lists))

        # 1. Generate DataFrame
        data = []
        for entry in entries:
            if not entry.results.guidellm_benchmarks:
                continue

            # Get unique name for this entry (includes flavor info)
            entry_name = entry.get_name(variables)

            for benchmark in entry.results.guidellm_benchmarks:
                data.append({
                    'Test Configuration': entry_name,
                    'Strategy': benchmark.strategy,
                    'Full Strategy Name': f"{benchmark.strategy} ({entry_name})",
                    'Request Latency (ms)': benchmark.request_latency_median * 1000,
                    'TTFT (ms)': benchmark.ttft_median,
                    'Concurrency': benchmark.request_concurrency,
                    'Request Rate': benchmark.request_rate,
                    'Tokens/s': benchmark.tokens_per_second
                })

        if not data:
            return None, ["No Guidellm benchmark data available"]

        df = pd.DataFrame(data)

        # Sort by request latency for better visualization
        df = df.sort_values('Request Latency (ms)')

        # 2. Generate plotly express plot
        title = _get_plot_title_with_load_shape(
            'Latency Overview by Strategy and Configuration',
            variables,
            settings
        )

        fig = px.bar(df,
                    hover_data=df.columns,
                    x='Full Strategy Name',
                    y='Request Latency (ms)',
                    color='Test Configuration',
                    text='Request Latency (ms)',
                    title=title)

        fig.update_traces(texttemplate='%{text:.1f}ms', textposition="outside")
        fig.update_layout(showlegend=True, xaxis_tickangle=-45)

        # 3. Generate summary text
        best_latency = df.loc[df['Request Latency (ms)'].idxmin()]
        worst_latency = df.loc[df['Request Latency (ms)'].idxmax()]
        avg_latency = df['Request Latency (ms)'].mean()

        best_ttft = df.loc[df['TTFT (ms)'].idxmin()]
        avg_ttft = df['TTFT (ms)'].mean()

        latency_spread = worst_latency['Request Latency (ms)'] - best_latency['Request Latency (ms)']

        # Configuration performance summary
        config_latency = df.groupby('Test Configuration')['Request Latency (ms)'].mean().sort_values()
        best_config = config_latency.index[0]
        worst_config = config_latency.index[-1]

        msg = []
        msg.append(f"Best request latency: {best_latency['Strategy']} in {best_latency['Test Configuration']} ({best_latency['Request Latency (ms)']:.1f} ms)")
        msg.append(html.Br())
        msg.append(f"Worst request latency: {worst_latency['Strategy']} in {worst_latency['Test Configuration']} ({worst_latency['Request Latency (ms)']:.1f} ms)")
        msg.append(html.Br())
        msg.append(f"Average request latency: {avg_latency:.1f} ms")
        msg.append(html.Br())
        msg.append(f"Latency spread: {latency_spread:.1f} ms")
        msg.append(html.Br())
        msg.append(html.Br())
        msg.append(f"Best configuration overall: {best_config} ({config_latency[best_config]:.1f} ms avg)")
        msg.append(html.Br())
        msg.append(f"Best TTFT: {best_ttft['Strategy']} in {best_ttft['Test Configuration']} ({best_ttft['TTFT (ms)']:.1f} ms)")
        msg.append(html.Br())
        msg.append(f"Average TTFT: {avg_ttft:.1f} ms")
        msg.append(html.Br())
        msg.append("Note: Bar color shows test configuration")

        # 4. Return fig, msg
        return fig, msg


class GuidellmTokensConcurrency():
    def __init__(self):
        self.name = "Guidellm Tokens vs Concurrency"
        self.id_name = "guidellm_tokens_concurrency"
        self.no_graph = False
        self.is_report = False

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        """
        Plot tokens per second vs concurrency to show token throughput scaling behavior
        """
        entries = list(common.Matrix.all_records(settings, setting_lists))

        # 1. Generate DataFrame
        data = []
        for entry in entries:
            if not entry.results.guidellm_benchmarks:
                continue

            # Get unique name for this entry (includes flavor info)
            entry_name = entry.get_name(variables)

            # Include all strategies - let's show the full picture
            for benchmark in entry.results.guidellm_benchmarks:
                if benchmark.strategy == "throughput":
                    continue

                # Determine strategy type for better grouping
                strategy_type = "Other"
                if 'constant' in benchmark.strategy.lower():
                    if 'arrival_rate' in benchmark.strategy.lower():
                        strategy_type = "Constant Arrival Rate"
                    elif 'concurrency' in benchmark.strategy.lower():
                        strategy_type = "Constant Concurrency"
                    else:
                        strategy_type = "Constant"
                elif 'sweep' in benchmark.strategy.lower():
                    strategy_type = "Sweep"
                elif 'ramp' in benchmark.strategy.lower():
                    strategy_type = "Ramp"

                data.append({
                    'Test Configuration': entry_name,
                    'Concurrency': benchmark.request_concurrency,
                    'Tokens/s': benchmark.output_tokens_per_second,
                    'Input Tokens/s': benchmark.input_tokens_per_second,
                    'Output Tokens/s': benchmark.output_tokens_per_second,
                    'Total Tokens/s': benchmark.tokens_per_second,
                    'Strategy': benchmark.strategy,
                    'Strategy Type': strategy_type,
                    'Request Rate (req/s)': benchmark.request_rate,
                    'TTFT (ms)': benchmark.ttft_median,
                    'Latency (ms)': benchmark.request_latency_median * 1000
                })

        if not data:
            return None, ["No Guidellm benchmark data available"]

        df = pd.DataFrame(data)

        # Sort by Concurrency for proper plot ordering
        df = df.sort_values('Concurrency')

        # 2. Generate plotly express plot with consistent color scheme
        # Sort configurations to ensure consistent color assignment
        configurations = sorted(df['Test Configuration'].unique())
        colors = px.colors.qualitative.Set1[:len(configurations)]
        color_map = {config: colors[i] for i, config in enumerate(configurations)}

        # Create title with load_shape if missing from variables
        title = _get_plot_title_with_load_shape(
            'Token Throughput vs Concurrency by Configuration (P50)<br><sub>Higher is better</sub>',
            variables,
            settings
        )

        fig = px.scatter(df,
                        hover_data=df.columns,
                        x='Concurrency',
                        y='Tokens/s',
                        color='Test Configuration',
                        color_discrete_map=color_map,
                        title=title)

        fig.update_traces(mode='lines+markers')
        fig.update_layout(showlegend=True)

        # 3. Generate summary text
        max_tokens = df['Tokens/s'].max()
        min_tokens = df['Tokens/s'].min()
        avg_tokens = df['Tokens/s'].mean()

        best_tokens = df.loc[df['Tokens/s'].idxmax()]
        best_efficiency = df.loc[(df['Tokens/s'] / df['Concurrency']).idxmax()]

        # Configuration breakdown
        config_counts = df['Test Configuration'].value_counts()
        strategy_counts = df['Strategy Type'].value_counts()
        total_strategies = len(df)

        # Performance analysis
        token_improvement = ((max_tokens - min_tokens) / min_tokens * 100) if min_tokens > 0 else 0

        # Find optimal concurrency ranges
        config_optimal = {}
        for config in df['Test Configuration'].unique():
            config_df = df[df['Test Configuration'] == config]
            if len(config_df) > 0:
                best_idx = config_df['Tokens/s'].idxmax()
                optimal_concurrency = config_df.loc[best_idx, 'Concurrency']
                optimal_tokens = config_df.loc[best_idx, 'Tokens/s']
                config_optimal[config] = (optimal_concurrency, optimal_tokens)

        msg = []
        msg.append(f"Analyzing {total_strategies} strategies across {len(config_counts)} test configurations:")
        msg.append(html.Br())
        for config, count in config_counts.items():
            msg.append(f"• {config}: {count} strategies")
            msg.append(html.Br())
        msg.append(html.Br())

        msg.append(f"Best token throughput: {best_tokens['Strategy']} in {best_tokens['Test Configuration']} ({max_tokens:.0f} tok/s at concurrency {best_tokens['Concurrency']:.0f})")
        msg.append(html.Br())
        msg.append(f"Token throughput range: {min_tokens:.0f} - {max_tokens:.0f} tok/s ({token_improvement:.1f}% improvement)")
        msg.append(html.Br())
        msg.append(f"Most efficient: {best_efficiency['Strategy']} in {best_efficiency['Test Configuration']} ({(best_efficiency['Tokens/s'] / best_efficiency['Concurrency']):.0f} tok/s per concurrency unit)")
        msg.append(html.Br())
        msg.append(html.Br())

        if config_optimal:
            msg.append("Optimal concurrency points by configuration:")
            msg.append(html.Br())
            for config, (opt_conc, opt_tokens) in config_optimal.items():
                msg.append(f"• {config}: {opt_conc:.0f} concurrency → {opt_tokens:.0f} tok/s")
                msg.append(html.Br())
            msg.append(html.Br())

        msg.append("Note: Color shows test configuration, lines connect points for each configuration")

        # 4. Return fig, msg
        return fig, msg


# Base class for latency analysis to eliminate code duplication
class GuidellmLatencyAnalysisBase():
    def __init__(self, metric_config):
        self.metric_config = metric_config
        self.name = f"Guidellm {metric_config['name']} Analysis"
        self.id_name = f"guidellm_{metric_config['name'].lower()}_analysis"
        self.no_graph = False
        self.is_report = False

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        """
        Generic plot for latency percentiles analysis across different strategies and configurations
        """
        config = self.metric_config
        entries = list(common.Matrix.all_records(settings, setting_lists))

        # 1. Generate DataFrame
        data = []
        for entry in entries:
            if not entry.results.guidellm_benchmarks:
                continue

            # Get unique name for this entry (includes flavor info)
            entry_name = entry.get_name(variables)

            for benchmark in entry.results.guidellm_benchmarks:
                if benchmark.strategy == "throughput":
                    continue

                # Get values with unit conversion
                p50_value = getattr(benchmark, config['p50_field']) * config['unit_conversion']
                p95_value = getattr(benchmark, config['p95_field']) * config['unit_conversion']

                data.append({
                    'Test Configuration': entry_name,
                    'Strategy': benchmark.strategy,
                    'Full Strategy Name': f"{benchmark.strategy} ({entry_name})",
                    'Concurrency': benchmark.request_concurrency,
                    'Request Rate (req/s)': benchmark.request_rate,
                    f'{config["name"]} P50 (ms)': p50_value,
                    f'{config["name"]} P95 (ms)': p95_value,
                    'Tokens/s': benchmark.tokens_per_second,
                })

        if not data:
            return None, ["No Guidellm benchmark data available"]

        df = pd.DataFrame(data)

        # 2. Generate plotly subplots for P50 and P95
        from plotly.subplots import make_subplots

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=(f'{config["name"]} P50 (Median)', f'{config["name"]} P95'),
            shared_xaxes=True,
            horizontal_spacing=0.1
        )

        # Get unique configurations and colors (consistent with other plots)
        configurations = sorted(df['Test Configuration'].unique())
        colors = px.colors.qualitative.Set1[:len(configurations)]
        color_map = {config_name: colors[i] for i, config_name in enumerate(configurations)}

        for i, config_name in enumerate(configurations):
            config_df = df[df['Test Configuration'] == config_name].sort_values('Concurrency')

            # Add P50 subplot (left)
            fig.add_trace(go.Scatter(
                x=config_df['Concurrency'],
                y=config_df[f'{config["name"]} P50 (ms)'],
                mode='lines+markers',
                name=f'{config_name}',
                line=dict(color=color_map[config_name], width=2),
                hovertemplate=f'<b>{config_name}</b><br>' +
                             'Concurrency: %{x}<br>' +
                             f'{config["name"]} P50: %{{y:.1f}} ms<br>' +
                             '<extra></extra>',
                showlegend=True
            ), row=1, col=1)

            # Add P95 subplot (right)
            fig.add_trace(go.Scatter(
                x=config_df['Concurrency'],
                y=config_df[f'{config["name"]} P95 (ms)'],
                mode='lines+markers',
                name=f'{config_name}',
                line=dict(color=color_map[config_name], width=2),
                hovertemplate=f'<b>{config_name}</b><br>' +
                             'Concurrency: %{x}<br>' +
                             f'{config["name"]} P95: %{{y:.1f}} ms<br>' +
                             '<extra></extra>',
                showlegend=False  # Don't duplicate legend
            ), row=1, col=2)

        # Create title with load_shape if missing from variables
        title = _get_plot_title_with_load_shape(
            f'{config["description"]} Analysis by Concurrency<br><sub>Lower is better</sub>',
            variables,
            settings
        )

        fig.update_layout(
            title_text=title,
            showlegend=True,
            hovermode='closest',
            height=500
        )

        # Update subplot axis labels
        fig.update_xaxes(title_text="Concurrency", row=1, col=1)
        fig.update_xaxes(title_text="Concurrency", row=1, col=2)
        fig.update_yaxes(title_text=f'{config["name"]} P50 (ms)', row=1, col=1)
        fig.update_yaxes(title_text=f'{config["name"]} P95 (ms)', row=1, col=2)

        # 3. Generate summary text
        p50_col = f'{config["name"]} P50 (ms)'
        p95_col = f'{config["name"]} P95 (ms)'

        best_p50_idx = df[p50_col].idxmin()
        best_p95_idx = df[p95_col].idxmin()

        best_p50 = df.loc[best_p50_idx]
        best_p95 = df.loc[best_p95_idx]

        # Calculate percentile spreads
        avg_p50 = df[p50_col].mean()
        avg_p95 = df[p95_col].mean()
        p50_range = df[p50_col].max() - df[p50_col].min()
        p95_range = df[p95_col].max() - df[p95_col].min()

        # Configuration analysis
        config_performance = df.groupby('Test Configuration').agg({
            p50_col: 'mean',
            p95_col: 'mean'
        }).sort_values(p50_col)

        best_config_name = config_performance.index[0]

        msg = []
        msg.append(f"🏆 Best {config['name']} P50: {best_p50['Strategy']} in {best_p50['Test Configuration']} ({best_p50[p50_col]:.1f} ms)")
        msg.append(html.Br())
        msg.append(f"🏆 Best {config['name']} P95: {best_p95['Strategy']} in {best_p95['Test Configuration']} ({best_p95[p95_col]:.1f} ms)")
        msg.append(html.Br())
        msg.append(f"📊 Average {config['name']} P50: {avg_p50:.1f} ms, P95: {avg_p95:.1f} ms")
        msg.append(html.Br())
        msg.append(f"📈 {config['name']} variability: P50 range {p50_range:.1f} ms, P95 range {p95_range:.1f} ms")
        msg.append(html.Br())
        msg.append(html.Br())
        msg.append(f"🥇 Best configuration overall: {best_config_name} (P50: {config_performance.loc[best_config_name, p50_col]:.1f} ms, P95: {config_performance.loc[best_config_name, p95_col]:.1f} ms)")
        msg.append(html.Br())
        msg.append(html.Br())
        msg.append(f"📝 Note: Left subplot shows P50 (median), right subplot shows P95. {config['note_text']}")
        msg.append(html.Br())
        msg.append(f"💡 {config['insight_text']}")

        # 4. Return fig, msg
        return fig, msg


# Specific analysis classes using the factorized base class
class GuidellmTTFTAnalysis(GuidellmLatencyAnalysisBase):
    def __init__(self):
        super().__init__({
            'name': 'TTFT',
            'description': 'TTFT Latency',
            'p50_field': 'ttft_median',
            'p95_field': 'ttft_p95',
            'unit_conversion': 1,  # Already in ms
            'note_text': 'P1 and P90 percentiles require additional data extraction from logs.',
            'insight_text': 'Lower TTFT values indicate better responsiveness. Look for configurations with consistently low and stable TTFT across concurrency levels.'
        })


class GuidellmTPOTAnalysis(GuidellmLatencyAnalysisBase):
    def __init__(self):
        super().__init__({
            'name': 'TPOT',
            'description': 'TPOT Latency',
            'p50_field': 'tpot_median',
            'p95_field': 'tpot_p95',
            'unit_conversion': 1000,  # Convert from seconds to ms
            'note_text': 'TPOT measures generation speed per token.',
            'insight_text': 'Lower TPOT values indicate faster token generation. Look for configurations with consistently low TPOT across concurrency levels.'
        })


class GuidellmITLAnalysis(GuidellmLatencyAnalysisBase):
    def __init__(self):
        super().__init__({
            'name': 'ITL',
            'description': 'ITL Latency',
            'p50_field': 'itl_median',
            'p95_field': 'itl_p95',
            'unit_conversion': 1000,  # Convert from seconds to ms
            'note_text': 'ITL measures streaming responsiveness.',
            'insight_text': 'Lower ITL values indicate smoother token streaming. Look for configurations with consistently low ITL for better user experience.'
        })


class GuidellmE2ELatencyAnalysis(GuidellmLatencyAnalysisBase):
    def __init__(self):
        super().__init__({
            'name': 'E2E Latency',
            'description': 'End-to-End Request Latency',
            'p50_field': 'request_latency_median',
            'p95_field': 'request_latency_p95',
            'unit_conversion': 1000,  # Convert from seconds to ms
            'note_text': 'E2E latency measures complete request duration.',
            'insight_text': 'Lower E2E values indicate faster overall response times. Look for configurations with consistently low E2E latency for better user experience.'
        })


class TokenThroughputAnalysis():
    def __init__(self):
        self.name = "Token Throughput Analysis"
        self.id_name = "token_throughput_analysis"
        self.no_graph = False
        self.is_report = False

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        """
        Analyze token generation throughput across strategies
        """
        ## rewrite below
        entries = list(common.Matrix.all_records(settings, setting_lists))

        # 1. Generate DataFrame
        data = []
        for entry in entries:
            if not entry.results.guidellm_benchmarks:
                continue

            # Get unique name for this entry (includes flavor info)
            entry_name = entry.get_name(variables)

            for benchmark in entry.results.guidellm_benchmarks:
                data.append({
                    'Test Configuration': entry_name,
                    'Strategy': benchmark.strategy,
                    'Full Strategy Name': f"{benchmark.strategy} ({entry_name})",
                    'Input Tokens/s': benchmark.input_tokens_per_second,
                    'Output Tokens/s': benchmark.output_tokens_per_second,
                    'Total Tokens/s': benchmark.tokens_per_second,
                    'Request Rate': benchmark.request_rate,
                    'TTFT (ms)': benchmark.ttft_median
                })

        if not data:
            return None, ["No Guidellm benchmark data available"]

        df = pd.DataFrame(data)
        # Sort by total token throughput
        df = df.sort_values('Total Tokens/s', ascending=False)

        # 2. Generate plotly express plot
        title = _get_plot_title_with_load_shape(
            'Token Throughput by Strategy and Configuration',
            variables,
            settings
        )

        fig = px.bar(df,
                    hover_data=df.columns,
                    x='Full Strategy Name',
                    y='Total Tokens/s',
                    color='Test Configuration',
                    text='Total Tokens/s',
                    title=title)

        fig.update_traces(texttemplate='%{text:.0f}', textposition="outside")
        fig.update_layout(showlegend=True, xaxis_tickangle=-45)

        # Add stacked breakdown as a secondary chart
        # Create stacked data for input/output breakdown
        df_stacked = df.melt(id_vars=['Strategy'],
                           value_vars=['Input Tokens/s', 'Output Tokens/s'],
                           var_name='Token Type', value_name='Tokens/s')

        # Create title with load_shape if missing from variables
        breakdown_title = _get_plot_title_with_load_shape(
            'Token Throughput Breakdown by Strategy',
            variables,
            settings
        )

        fig_stacked = px.bar(df_stacked,
                           x='Strategy',
                           y='Tokens/s',
                           color='Token Type',
                           title=breakdown_title)

        fig_stacked.update_layout(xaxis_tickangle=-45)

        # Use the main chart for now
        # 3. Generate summary text
        max_tokens = df['Total Tokens/s'].max()
        min_tokens = df['Total Tokens/s'].min()
        avg_tokens = df['Total Tokens/s'].mean()

        best_strategy = df.loc[df['Total Tokens/s'].idxmax()]
        improvement = ((max_tokens - min_tokens) / min_tokens * 100) if min_tokens > 0 else 0

        # Configuration performance summary
        config_tokens = df.groupby('Test Configuration')['Total Tokens/s'].mean().sort_values(ascending=False)
        best_config = config_tokens.index[0]

        msg = []
        msg.append(f"Highest token throughput: {best_strategy['Strategy']} in {best_strategy['Test Configuration']} ({max_tokens:.0f} tok/s)")
        msg.append(html.Br())
        msg.append(f"Lowest token throughput: {min_tokens:.0f} tok/s")
        msg.append(html.Br())
        msg.append(f"Average token throughput: {avg_tokens:.0f} tok/s")
        msg.append(html.Br())
        msg.append(f"Performance improvement: {improvement:.1f}% (best vs worst)")
        msg.append(html.Br())
        msg.append(html.Br())
        msg.append(f"Best configuration overall: {best_config} ({config_tokens[best_config]:.0f} tok/s avg)")

        # 4. Return fig, msg
        return fig, msg
