#!/usr/bin/env python3

"""
Test script for LLM-D inference visualization parsing

Usage: python test_parser.py /path/to/test/results
"""

import sys
import pathlib
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent))

from projects.llm_d.visualizations.llmd_inference.store.lts_parser import parse_directory

def test_parsing(results_path):
    """Test the parsing of LLM-D inference results"""

    results_path = pathlib.Path(results_path)

    if not results_path.exists():
        logging.error(f"Results path does not exist: {results_path}")
        return False

    try:
        logging.info(f"Parsing results from: {results_path}")
        payload = parse_directory(results_path)

        # Print summary of parsed data
        print("\n" + "="*60)
        print("PARSING RESULTS SUMMARY")
        print("="*60)

        results = payload.results
        kpis = payload.kpis

        print(f"Test Name: {results.test_name}")
        print(f"Test Timestamp: {results.test_timestamp}")
        print(f"Test Success: {results.test_success}")

        if results.test_failure_reason:
            print(f"Failure Reason: {results.test_failure_reason}")

        print(f"\nData Sources:")
        print(f"  Multi-turn log: {'✓' if results.multiturn_log_path else '✗'}")
        print(f"  Guidellm log: {'✓' if results.guidellm_log_path else '✗'}")
        print(f"  Prometheus dump: {'✓' if results.prometheus_path else '✗'}")

        # Multi-turn benchmark results
        if results.multiturn_benchmark:
            mb = results.multiturn_benchmark
            print(f"\nMulti-turn Benchmark:")
            print(f"  Total time: {mb.total_time:.1f}s")
            print(f"  Total requests: {mb.total_requests}")
            print(f"  Completed conversations: {mb.completed_conversations}/{mb.total_conversations}")
            print(f"  Requests per second: {mb.requests_per_second:.2f}")
            print(f"  TTFT P50/P95: {mb.ttft_p50:.1f}ms / {mb.ttft_p95:.1f}ms")
            print(f"  TTFT by turn count: {len(mb.ttft_by_turn)}")
            print(f"  TTFT by doc type: {list(mb.ttft_by_doc_type.keys())}")
            if mb.speedup_ratio:
                print(f"  Prefix caching speedup: {mb.speedup_ratio:.2f}x")

        # Guidellm benchmark results
        if results.guidellm_benchmarks:
            print(f"\nGuidellm Benchmarks: {len(results.guidellm_benchmarks)} strategies")
            best_strategy = max(results.guidellm_benchmarks, key=lambda x: x.request_rate)
            print(f"  Best strategy: {best_strategy.strategy}")
            print(f"  Best request rate: {best_strategy.request_rate:.2f} req/s")
            print(f"  Best TTFT: {best_strategy.ttft_median:.1f}ms")

        # KPIs
        print(f"\nKey Performance Indicators:")
        for key, value in kpis.items():
            if value is not None:
                print(f"  {key}: {value}")

        print("\n" + "="*60)
        print("PARSING COMPLETED SUCCESSFULLY")
        print("="*60)

        return True

    except Exception as e:
        logging.error(f"Error parsing results: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_parser.py /path/to/test/results")
        print("Example: python test_parser.py /tmp/topsail_20260220-1059/000__llm_d_testing")
        sys.exit(1)

    success = test_parsing(sys.argv[1])
    sys.exit(0 if success else 1)