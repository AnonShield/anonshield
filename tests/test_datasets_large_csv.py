#!/usr/bin/env python3
"""
Test --use-datasets flag impact on large CSV with Presidio strategy.
Compares performance with and without the flag.
"""

import subprocess
import time
import sys
import re

def run_test(use_datasets=False):
    """Run anonymization test and return time elapsed."""
    flag = "--use-datasets" if use_datasets else ""
    cmd = f"python3 anon.py cve_dataset_mock_cais_stratified.csv {flag} --anonymization-strategy presidio --csv-chunk-size 5000 --no-report --overwrite --log-level INFO --output-dir output/test_datasets_csv_presidio"
    
    print(f"\n{'='*70}")
    print(f"Testing: {'WITH --use-datasets' if use_datasets else 'WITHOUT --use-datasets (baseline)'}")
    print(f"{'='*70}")
    print(f"Command: {cmd}\n")
    
    start = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    elapsed = time.time() - start
    
    if result.returncode != 0:
        print(f"❌ FAILED (exit code {result.returncode})")
        print(f"Last 1000 chars of stderr:\n{result.stderr[-1000:]}")
        return None
    
    # Extract batch size from logs if available
    batch_size = None
    if "batch_size" in result.stderr.lower() or "batch" in result.stderr.lower():
        match = re.search(r'batch[_ ]size.*?(\d+)', result.stderr, re.IGNORECASE)
        if match:
            batch_size = match.group(1)
    
    print(f"✅ COMPLETED in {elapsed:.1f}s")
    if batch_size:
        print(f"   Detected batch_size: {batch_size}")
    
    return elapsed

def main():
    print("="*70)
    print("Testing --use-datasets Flag with Large CSV (246MB, presidio)")
    print("="*70)
    print("\nFile: cve_dataset_mock_cais_stratified.csv (248MB, 70,952 rows)")
    print("Strategy: presidio (comprehensive, CPU-bound)")
    print("Chunk size: 5000 rows")
    
    # Test 1: Baseline (without --use-datasets)
    time_without = run_test(use_datasets=False)
    
    if time_without is None:
        print("\n❌ Baseline test failed. Aborting.")
        sys.exit(1)
    
    # Test 2: With --use-datasets
    time_with = run_test(use_datasets=True)
    
    if time_with is None:
        print("\n❌ Test with --use-datasets failed. Aborting.")
        sys.exit(1)
    
    # Results
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"Time WITHOUT --use-datasets: {time_without:.1f}s")
    print(f"Time WITH --use-datasets:    {time_with:.1f}s")
    print(f"Difference:                  {abs(time_with - time_without):.1f}s")
    
    if time_with < time_without:
        improvement = ((time_without - time_with) / time_without) * 100
        speedup = time_without / time_with
        print(f"Speedup:                     {speedup:.2f}x")
        print(f"Improvement:                 {improvement:.1f}%")
        print(f"\n✅ --use-datasets is FASTER by {improvement:.1f}%")
    else:
        regression = ((time_with - time_without) / time_without) * 100
        slowdown = time_with / time_without
        print(f"Slowdown:                    {slowdown:.2f}x")
        print(f"Regression:                  {regression:.1f}%")
        print(f"\n⚠️  --use-datasets is SLOWER by {regression:.1f}%")
        print("\nPossible causes:")
        print("  • Batch size too large (128) causes memory pressure")
        print("  • Presidio CPU overhead scales badly with batch size")
        print("  • Deduplication overhead increases with batch size")
        print("\nRecommendation: Don't use --use-datasets with presidio + large CSV")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    main()
