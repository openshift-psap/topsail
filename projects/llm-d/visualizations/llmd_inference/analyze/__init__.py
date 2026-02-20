# Analysis functions for LLM-D inference results

def analyze_multiturn_performance(results):
    """
    Analyze multi-turn benchmark performance and provide insights
    """
    if not results.multiturn_benchmark:
        return "No multi-turn benchmark data available"

    mb = results.multiturn_benchmark
    insights = []

    # Analyze completion rate
    if mb.total_conversations == 0:
        completion_rate = 0.0
        insights.append("⚠ No conversations completed (total conversations: 0)")
    else:
        completion_rate = mb.completed_conversations / mb.total_conversations
        if completion_rate < 0.95:
            insights.append(f"⚠ Low completion rate: {completion_rate:.1%}")
        else:
            insights.append(f"✓ Good completion rate: {completion_rate:.1%}")

    # Analyze TTFT performance
    if mb.ttft_p95 > 10000:  # > 10 seconds
        insights.append("⚠ High TTFT P95 indicates potential performance issues")
    elif mb.ttft_p95 < 2000:  # < 2 seconds
        insights.append("✓ Excellent TTFT performance")

    # Analyze prefix caching effectiveness
    if mb.speedup_ratio and mb.speedup_ratio > 1.5:
        insights.append(f"✓ Effective prefix caching: {mb.speedup_ratio:.1f}x speedup")
    elif mb.speedup_ratio and mb.speedup_ratio < 1.2:
        insights.append("⚠ Limited prefix caching benefit")

    return "\n".join(insights)

def analyze_guidellm_performance(results):
    """
    Analyze Guidellm benchmark performance and provide insights
    """
    if not results.guidellm_benchmarks:
        return "No Guidellm benchmark data available"

    insights = []
    benchmarks = results.guidellm_benchmarks

    # Find best performing strategy
    best_strategy = max(benchmarks, key=lambda x: x.request_rate)
    insights.append(f"✓ Best strategy: {best_strategy.strategy} ({best_strategy.request_rate:.2f} req/s)")

    # Analyze scaling behavior
    constant_strategies = [b for b in benchmarks if 'constant' in b.strategy]
    if len(constant_strategies) > 2:
        rates = [b.request_rate for b in constant_strategies]
        min_rate = min(rates)
        if min_rate > 0 and max(rates) / min_rate > 3:
            insights.append("✓ Good throughput scaling with concurrency")
        elif min_rate == 0:
            insights.append("⚠ Cannot analyze scaling (zero request rate detected)")
        else:
            insights.append("⚠ Limited throughput scaling")

    # Analyze latency consistency
    latencies = [b.request_latency_median for b in benchmarks]
    min_latency = min(latencies)
    if min_latency > 0 and max(latencies) / min_latency > 10:
        insights.append("⚠ High latency variance across strategies")
    elif min_latency == 0:
        insights.append("⚠ Cannot analyze latency consistency (zero latency detected)")
    else:
        insights.append("✓ Consistent latency across strategies")

    return "\n".join(insights)

def analyze_overall_performance(results, kpis):
    """
    Provide overall performance analysis and recommendations
    """
    insights = []

    # Overall test success
    if results.test_success:
        insights.append("✓ Test completed successfully")
    else:
        insights.append(f"✗ Test failed: {results.test_failure_reason}")

    # Performance score analysis
    if 'overall_performance_score' in kpis and kpis['overall_performance_score']:
        score = kpis['overall_performance_score']
        if score > 0.8:
            insights.append(f"✓ Excellent performance score: {score:.3f}")
        elif score > 0.6:
            insights.append(f"✓ Good performance score: {score:.3f}")
        else:
            insights.append(f"⚠ Performance needs improvement: {score:.3f}")

    # Recommendations
    recommendations = []

    if results.multiturn_benchmark and results.multiturn_benchmark.ttft_p95 > 5000:
        recommendations.append("• Consider optimizing model loading or caching")

    if results.guidellm_benchmarks:
        max_rate = max(b.request_rate for b in results.guidellm_benchmarks)
        if max_rate < 1.0:
            recommendations.append("• Consider scaling up inference resources")

    if recommendations:
        insights.extend(["", "Recommendations:"] + recommendations)

    return "\n".join(insights)