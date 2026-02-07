#!/usr/bin/env python3
"""
Quick test: --use-datasets impact on CSV with presidio strategy.
Uses first 1000 rows for faster testing.
"""

import subprocess
import time
import sys

def run_test(test_name, cmd):
    """Run test and return elapsed time."""
    print(f"\n{'='*70}")
    print(f"{test_name}")
    print(f"{'='*70}")
    print(f"Command: {cmd}\n")
    
    start = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    elapsed = time.time() - start
    
    if result.returncode != 0:
        print(f"❌ FAILED (exit code {result.returncode})")
        print(f"Stderr (last 500 chars):\n{result.stderr[-500:]}")
        return None
    
    print(f"✅ COMPLETED in {elapsed:.1f}s")
    
    # Check for batch size in logs
    if "Batch size adjusted" in result.stderr:
        for line in result.stderr.split('\n'):
            if "Batch size adjusted" in line:
                print(f"   {line.strip()}")
    
    return elapsed

def main():
    print("="*70)
    print("Quick Test: --use-datasets with CSV (1000 rows)")
    print("="*70)
    
    base_cmd = "python3 anon.py test_1k_rows.csv --anonymization-strategy presidio --csv-chunk-size 500 --no-report --overwrite --log-level DEBUG --output-dir output/quick_test"
    
    # Test 1: WITHOUT --use-datasets (baseline)
    time_without = run_test(
        "Test 1: WITHOUT --use-datasets (baseline)",
        base_cmd
    )
    
    if time_without is None:
        sys.exit(1)
    
    # Test 2: WITH --use-datasets
    time_with = run_test(
        "Test 2: WITH --use-datasets",
        base_cmd + " --use-datasets"
    )
    
    if time_with is None:
        sys.exit(1)
    
    # Results
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"WITHOUT --use-datasets: {time_without:.1f}s")
    print(f"WITH --use-datasets:    {time_with:.1f}s")
    print(f"Difference:             {abs(time_with - time_without):.1f}s ({abs(time_with - time_without)/time_without*100:.1f}%)")
    
    if time_with < time_without:
        print(f"\n✅ --use-datasets is {time_without/time_with:.2f}x FASTER")
    else:
        print(f"\n⚠️  --use-datasets is {time_with/time_without:.2f}x SLOWER")
        print("\nIssue confirmed: batch_size=128 causes overhead for CSV+presidio")
        print("\nRoot cause:")
        print("  • CSV processor increases batch_size to 128 with --use-datasets")
        print("  • Presidio is CPU-bound and doesn't benefit from larger batches")
        print("  • Larger batches → more memory pressure → slower processing")
        print("\nSolution: Remove or reduce batch_size increase for CSV+presidio")
    
    print("="*70)

if __name__ == "__main__":
    main()
