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
                        color='Strategy Type',
                        symbol='Strategy Type',
                        size='Tokens/s',
                        text='Strategy',
                        title='Request Throughput vs Concurrency (All Strategies)')

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

        # Strategy type breakdown
        strategy_counts = df['Strategy Type'].value_counts()
        total_strategies = len(df)

        performance_ratio = ((max_rate - min_rate) / min_rate * 100) if min_rate > 0 else 0

        msg = []
        msg.append(f"Showing {total_strategies} strategies across {len(strategy_counts)} types:")
        msg.append(html.Br())
        for strategy_type, count in strategy_counts.items():
            msg.append(f"• {strategy_type}: {count} strategies")
            msg.append(html.Br())
        msg.append(html.Br())
        msg.append(f"Best performing: {best_strategy['Strategy']} ({max_rate:.2f} req/s)")
        msg.append(html.Br())
        msg.append(f"Performance range: {min_rate:.2f} - {max_rate:.2f} req/s ({performance_ratio:.1f}% spread)")
        msg.append(html.Br())
        msg.append("Note: Bubble size shows token throughput, shape/color shows strategy type")

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

            for benchmark in entry.results.guidellm_benchmarks:
                if benchmark.strategy == "throughput":
                    continue

                data.append({
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
                        color='Strategy',
                        size='Tokens/s',
                        text='Strategy',
                        title='Latency vs Throughput Trade-off')

        fig.update_traces(textposition="top center")
        fig.update_layout(showlegend=True)

        # 3. Generate summary text
        best_throughput = df.loc[df['Request Rate (req/s)'].idxmax()]
        best_latency = df.loc[df['Latency (ms)'].idxmin()]

        # Calculate efficiency (high throughput, low latency)
        df['Efficiency'] = df['Request Rate (req/s)'] / df['Latency (ms)']
        most_efficient = df.loc[df['Efficiency'].idxmax()]

        msg = []
        msg.append(f"Highest throughput: {best_throughput['Strategy']} ({best_throughput['Request Rate (req/s)']:.2f} req/s)")
        msg.append(html.Br())
        msg.append(f"Lowest latency: {best_latency['Strategy']} ({best_latency['Latency (ms)']:.1f} ms)")
        msg.append(html.Br())
        msg.append(f"Most efficient: {most_efficient['Strategy']} ({most_efficient['Efficiency']:.2f} req/s per ms)")
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

            for benchmark in entry.results.guidellm_benchmarks:
                data.append({
                    'Strategy': benchmark.strategy,
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
                    x='Strategy',
                    y='Request Latency (ms)',
                    color='TTFT (ms)',
                    text='Request Latency (ms)',
                    color_continuous_scale='RdYlGn_r',  # Red=high latency, Green=low latency
                    title='Latency Overview by Strategy')

        fig.update_traces(texttemplate='%{text:.1f}ms', textposition="outside")
        fig.update_layout(showlegend=True, xaxis_tickangle=-45)

        # 3. Generate summary text
        best_latency = df.loc[df['Request Latency (ms)'].idxmin()]
        worst_latency = df.loc[df['Request Latency (ms)'].idxmax()]
        avg_latency = df['Request Latency (ms)'].mean()

        best_ttft = df.loc[df['TTFT (ms)'].idxmin()]
        avg_ttft = df['TTFT (ms)'].mean()

        latency_spread = worst_latency['Request Latency (ms)'] - best_latency['Request Latency (ms)']

        msg = []
        msg.append(f"Best request latency: {best_latency['Strategy']} ({best_latency['Request Latency (ms)']:.1f} ms)")
        msg.append(html.Br())
        msg.append(f"Worst request latency: {worst_latency['Strategy']} ({worst_latency['Request Latency (ms)']:.1f} ms)")
        msg.append(html.Br())
        msg.append(f"Average request latency: {avg_latency:.1f} ms")
        msg.append(html.Br())
        msg.append(f"Latency spread: {latency_spread:.1f} ms")
        msg.append(html.Br())
        msg.append(html.Br())
        msg.append(f"Best TTFT: {best_ttft['Strategy']} ({best_ttft['TTFT (ms)']:.1f} ms)")
        msg.append(html.Br())
        msg.append(f"Average TTFT: {avg_ttft:.1f} ms")
        msg.append(html.Br())
        msg.append("Note: Bar color shows TTFT (red=high, green=low)")

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

            for benchmark in entry.results.guidellm_benchmarks:
                data.append({
                    'Strategy': benchmark.strategy,
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
                    x='Strategy',
                    y='Total Tokens/s',
                    color='Strategy',
                    text='Total Tokens/s',
                    title='Token Throughput by Strategy')

        fig.update_traces(texttemplate='%{text:.0f}', textposition="outside")
        fig.update_layout(showlegend=False, xaxis_tickangle=-45)

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

        msg = []
        msg.append(f"Highest token throughput: {best_strategy['Strategy']} ({max_tokens:.0f} tok/s)")
        msg.append(html.Br())
        msg.append(f"Lowest token throughput: {min_tokens:.0f} tok/s")
        msg.append(html.Br())
        msg.append(f"Average token throughput: {avg_tokens:.0f} tok/s")
        msg.append(html.Br())
        msg.append(f"Performance improvement: {improvement:.1f}% (best vs worst)")

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
            entry_name = getattr(entry, 'name', f"Test {len(data) + 1}")

            # Extract TTFT by turn data
            if hasattr(benchmark, 'ttft_by_turn') and benchmark.ttft_by_turn:
                for turn_num, ttft_value in benchmark.ttft_by_turn.items():
                    data.append({
                        'Turn Number': turn_num,
                        'TTFT (ms)': ttft_value,
                        'Test': entry_name,
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
                     color='Test',
                     markers=True,
                     range_y=[0, max_ttft * 1.1],
                     title='TTFT by Turn Number - Prefix Caching Effects')

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
        # Calculate prefix caching effectiveness
        turn_1_data = df[df['Turn Number'] == 1]
        later_turns_data = df[df['Turn Number'] > 1]

        if not turn_1_data.empty and not later_turns_data.empty:
            avg_turn_1 = turn_1_data['TTFT (ms)'].mean()
            avg_later = later_turns_data['TTFT (ms)'].mean()
            speedup = avg_turn_1 / avg_later if avg_later > 0 else 1
            improvement = ((avg_turn_1 - avg_later) / avg_turn_1 * 100) if avg_turn_1 > 0 else 0

            msg = []
            msg.append(f"Turn 1 average TTFT: {avg_turn_1:.1f} ms")
            msg.append(html.Br())
            msg.append(f"Later turns average TTFT: {avg_later:.1f} ms")
            msg.append(html.Br())
            msg.append(f"Prefix caching speedup: {speedup:.2f}x")
            msg.append(html.Br())
            msg.append(f"Performance improvement: {improvement:.1f}%")
            msg.append(html.Br())

            # Effectiveness rating
            if speedup > 2:
                effectiveness = "🟢 Excellent"
            elif speedup > 1.5:
                effectiveness = "🟡 Good"
            elif speedup > 1.1:
                effectiveness = "🟠 Moderate"
            else:
                effectiveness = "🔴 Minimal"

            msg.append(f"Prefix caching effectiveness: {effectiveness}")
        else:
            msg = ["Insufficient data to calculate prefix caching effectiveness"]

        # Add turn range info
        min_turn = df['Turn Number'].min()
        max_turn = df['Turn Number'].max()
        msg.append(html.Br())
        msg.append(f"Turn range analyzed: {min_turn} to {max_turn}")

        # 4. Return fig, msg
        return fig, msg
