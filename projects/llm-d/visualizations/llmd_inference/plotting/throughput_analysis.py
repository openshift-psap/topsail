import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    GuidellmThroughputScaling()
    GuidellmLatencyVsThroughput()
    GuidellmLatencyOverview()

    TokenThroughputAnalysis()
    MultiturnTTFTByTurn()

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

        # 2. Generate plotly express plot
        fig = px.scatter(df,
                        hover_data=df.columns,
                        x='Concurrency',
                        y='Request Rate (req/s)',
                        color='Test Configuration',
                        symbol='Strategy Type',
                        size='Tokens/s',
                        text='Strategy',
                        title='Request Throughput vs Concurrency by Configuration')

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

        # 2. Generate plotly express plot
        fig = px.scatter(df,
                        hover_data=df.columns,
                        x='Request Rate (req/s)',
                        y='Latency (ms)',
                        color='Test Configuration',
                        symbol='Test Configuration',
                        size='Tokens/s',
                        text='Strategy',
                        title='Latency vs Throughput Trade-off by Configuration')

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
        fig = px.bar(df,
                    hover_data=df.columns,
                    x='Full Strategy Name',
                    y='Request Latency (ms)',
                    color='Test Configuration',
                    text='Request Latency (ms)',
                    title='Latency Overview by Strategy and Configuration')

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
        fig = px.bar(df,
                    hover_data=df.columns,
                    x='Full Strategy Name',
                    y='Total Tokens/s',
                    color='Test Configuration',
                    text='Total Tokens/s',
                    title='Token Throughput by Strategy and Configuration')

        fig.update_traces(texttemplate='%{text:.0f}', textposition="outside")
        fig.update_layout(showlegend=True, xaxis_tickangle=-45)

        # Add stacked breakdown as a secondary chart
        # Create stacked data for input/output breakdown
        df_stacked = df.melt(id_vars=['Strategy'],
                           value_vars=['Input Tokens/s', 'Output Tokens/s'],
                           var_name='Token Type', value_name='Tokens/s')

        fig_stacked = px.bar(df_stacked,
                           x='Strategy',
                           y='Tokens/s',
                           color='Token Type',
                           title='Token Throughput Breakdown by Strategy')

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


class MultiturnTTFTByTurn():
    def __init__(self):
        self.name = "Multi-turn TTFT by Turn Number"
        self.id_name = "multiturn_ttft_by_turn"
        self.no_graph = False
        self.is_report = False

        table_stats.TableStats._register_stat(self)
        common.Matrix.settings["stats"].add(self.name)

    def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
        """
        Plot TTFT by turn number to show prefix caching effects
        """
        ## rewrite below
        entries = list(common.Matrix.all_records(settings, setting_lists))

        # 1. Generate DataFrame
        data = []
        for entry in entries:
            if not hasattr(entry.results, 'multiturn_benchmark') or not entry.results.multiturn_benchmark:
                continue

            benchmark = entry.results.multiturn_benchmark
            # Get unique name for this entry (includes flavor info)
            entry_name = entry.get_name(variables)

            # Extract TTFT by turn data
            if hasattr(benchmark, 'ttft_by_turn') and benchmark.ttft_by_turn:
                for turn_num, ttft_value in benchmark.ttft_by_turn.items():
                    data.append({
                        'Turn Number': turn_num,
                        'TTFT (ms)': ttft_value,
                        'Test Configuration': entry_name,
                        'Requests/sec': benchmark.requests_per_second,
                        'Total Requests': benchmark.total_requests,
                        'Completed Conversations': f"{benchmark.completed_conversations}/{benchmark.total_conversations}"
                    })

        if not data:
            return None, ["No multi-turn TTFT by turn data available"]

        df = pd.DataFrame(data)

        # 2. Generate plotly express plot
        max_ttft = df['TTFT (ms)'].max()
        fig = px.line(df,
                     hover_data=df.columns,
                     x='Turn Number',
                     y='TTFT (ms)',
                     color='Test Configuration',
                     markers=True,
                     range_y=[0, max_ttft * 1.1],
                     title='TTFT by Turn Number - Prefix Caching Effects by Configuration')

        fig.update_traces(mode='lines+markers')
        fig.update_layout(showlegend=True)
        fig.update_xaxes(dtick=1)  # Show every turn number

        # Add annotation about prefix caching
        fig.add_annotation(
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            text="Lower TTFT in later turns indicates effective prefix caching",
            showarrow=False,
            font=dict(size=10),
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="gray",
            borderwidth=1
        )

        # 3. Generate summary text
        # Calculate prefix caching effectiveness overall and per configuration
        turn_1_data = df[df['Turn Number'] == 1]
        later_turns_data = df[df['Turn Number'] > 1]

        msg = []

        if not turn_1_data.empty and not later_turns_data.empty:
            # Overall effectiveness
            avg_turn_1 = turn_1_data['TTFT (ms)'].mean()
            avg_later = later_turns_data['TTFT (ms)'].mean()
            speedup = avg_turn_1 / avg_later if avg_later > 0 else 1
            improvement = ((avg_turn_1 - avg_later) / avg_turn_1 * 100) if avg_turn_1 > 0 else 0

            msg.append(f"Overall Turn 1 average TTFT: {avg_turn_1:.1f} ms")
            msg.append(html.Br())
            msg.append(f"Overall later turns average TTFT: {avg_later:.1f} ms")
            msg.append(html.Br())
            msg.append(f"Overall prefix caching speedup: {speedup:.2f}x")
            msg.append(html.Br())
            msg.append(f"Overall performance improvement: {improvement:.1f}%")
            msg.append(html.Br())
            msg.append(html.Br())

            # Per-configuration effectiveness
            configurations = df['Test Configuration'].unique()
            msg.append("Per-configuration analysis:")
            msg.append(html.Br())
            for config in configurations:
                config_df = df[df['Test Configuration'] == config]
                config_turn_1 = config_df[config_df['Turn Number'] == 1]['TTFT (ms)'].mean()
                config_later = config_df[config_df['Turn Number'] > 1]['TTFT (ms)'].mean()

                if not pd.isna(config_turn_1) and not pd.isna(config_later) and config_later > 0:
                    config_speedup = config_turn_1 / config_later
                    msg.append(f"• {config}: {config_speedup:.2f}x speedup")
                    msg.append(html.Br())

            # Overall effectiveness rating
            if speedup > 2:
                effectiveness = "🟢 Excellent"
            elif speedup > 1.5:
                effectiveness = "🟡 Good"
            elif speedup > 1.1:
                effectiveness = "🟠 Moderate"
            else:
                effectiveness = "🔴 Minimal"

            msg.append(html.Br())
            msg.append(f"Overall prefix caching effectiveness: {effectiveness}")
        else:
            msg.append("Insufficient data to calculate prefix caching effectiveness")

        # Add turn range info
        min_turn = df['Turn Number'].min()
        max_turn = df['Turn Number'].max()
        msg.append(html.Br())
        msg.append(f"Turn range analyzed: {min_turn} to {max_turn}")
        msg.append(html.Br())
        msg.append(f"Configurations tested: {', '.join(df['Test Configuration'].unique())}")

        # 4. Return fig, msg
        return fig, msg
