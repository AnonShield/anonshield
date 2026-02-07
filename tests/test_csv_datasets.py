#!/usr/bin/env python3
"""
Test --use-datasets flag with large CSV file (similar to user's use case).
Measures performance improvement and GPU warning elimination.
"""
import os
import sys
import time
import subprocess
import pandas as pd
from pathlib import Path

def create_test_csv(filename, num_rows=1000):
    """Create a test CSV with repetitive data (simulates real vulnerability scans)"""
    print(f"Creating test CSV with {num_rows} rows...")
    
    # Simulating CVE data with repetition (like real scans)
    data = {
        'cve_id': [f'CVE-2023-{1000 + (i % 100)}' for i in range(num_rows)],
        'severity': ['CRITICAL' if i % 4 == 0 else 'HIGH' if i % 3 == 0 else 'MEDIUM' for i in range(num_rows)],
        'description': [f'Vulnerability in Apache HTTP Server {2.4 + (i % 10)} allows remote attacker John Smith to execute arbitrary code' for i in range(num_rows)],
        'affected_system': [f'server-{i % 50}.example.com' for i in range(num_rows)],
        'reporter_email': [f'security-team{i % 20}@acmecorp.com' for i in range(num_rows)],
        'cvss_score': [7.5 + (i % 30) / 10 for i in range(num_rows)],
        'date_discovered': [f'2024-{(i % 12) + 1:02d}-15' for i in range(num_rows)],
        'notes': [f'Reported by Jane Doe from security team. Contact: +1-555-{1000 + (i % 100)}' for i in range(num_rows)],
    }
    
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    
    file_size = os.path.getsize(filename)
    print(f"✅ Created {filename} ({file_size / 1024:.2f} KB, {num_rows} rows)")
    return file_size

def run_with_timing(cmd):
    """Run command and capture timing + GPU warning"""
    print(f"\nRunning: {cmd}")
    start = time.time()
    
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    
    elapsed = time.time() - start
    
    # Check for GPU warning
    gpu_warning = "pipelines sequentially on GPU" in result.stderr
    
    # Check for optimization logs
    deduplication_used = "deduplication" in result.stderr.lower()
    
    return {
        'elapsed': elapsed,
        'exit_code': result.returncode,
        'gpu_warning': gpu_warning,
        'deduplication': deduplication_used,
        'stderr': result.stderr,
        'stdout': result.stdout
    }

def main():
    print("="*70)
    print("Testing --use-datasets Flag with CSV Data")
    print("="*70)
    
    # Setup
    test_csv = "test_large_dataset.csv"
    num_rows = 5000  # Adjust based on your needs
    
    if not os.path.exists(test_csv):
        file_size = create_test_csv(test_csv, num_rows)
    else:
        file_size = os.path.getsize(test_csv)
        print(f"Using existing {test_csv} ({file_size / 1024:.2f} KB)")
    
    # Set secret key if not set
    if not os.environ.get('ANON_SECRET_KEY'):
        os.environ['ANON_SECRET_KEY'] = 'test-key-12345678901234567890123456789012'
    
    base_cmd = f"python3 anon.py {test_csv} --no-report --overwrite --log-level INFO"
    
    # Test 1: Baseline (without --use-datasets)
    print("\n" + "="*70)
    print("TEST 1: Baseline (WITHOUT --use-datasets)")
    print("="*70)
    
    result_baseline = run_with_timing(
        f"{base_cmd} --output-dir output/csv_baseline"
    )
    
    if result_baseline['exit_code'] == 0:
        print(f"✅ Success in {result_baseline['elapsed']:.2f}s")
    else:
        print(f"❌ Failed with exit code {result_baseline['exit_code']}")
        print("Last 500 chars of error:")
        print(result_baseline['stderr'][-500:])
        return
    
    # Test 2: With --use-datasets
    print("\n" + "="*70)
    print("TEST 2: Optimized (WITH --use-datasets)")
    print("="*70)
    
    result_optimized = run_with_timing(
        f"{base_cmd} --output-dir output/csv_optimized --use-datasets"
    )
    
    if result_optimized['exit_code'] == 0:
        print(f"✅ Success in {result_optimized['elapsed']:.2f}s")
    else:
        print(f"❌ Failed with exit code {result_optimized['exit_code']}")
        print("Last 500 chars of error:")
        print(result_optimized['stderr'][-500:])
        return
    
    # Analysis
    print("\n" + "="*70)
    print("PERFORMANCE ANALYSIS")
    print("="*70)
    
    time_baseline = result_baseline['elapsed']
    time_optimized = result_optimized['elapsed']
    
    improvement_pct = ((time_baseline - time_optimized) / time_baseline * 100)
    speedup = time_baseline / time_optimized if time_optimized > 0 else 0
    
    print(f"\nFile size: {file_size / 1024:.2f} KB ({num_rows} rows)")
    print(f"\n{'Metric':<30} {'Baseline':<15} {'Optimized':<15} {'Change'}")
    print("-" * 70)
    print(f"{'Execution time':<30} {time_baseline:>10.2f}s    {time_optimized:>10.2f}s    {improvement_pct:>+6.1f}%")
    print(f"{'GPU warning present':<30} {str(result_baseline['gpu_warning']):<15} {str(result_optimized['gpu_warning']):<15}")
    print(f"{'Deduplication detected':<30} {str(result_baseline['deduplication']):<15} {str(result_optimized['deduplication']):<15}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    if improvement_pct > 5:
        print(f"✅ SIGNIFICANT IMPROVEMENT: {improvement_pct:.1f}% faster ({speedup:.2f}x speedup)")
    elif improvement_pct > 0:
        print(f"✅ MODEST IMPROVEMENT: {improvement_pct:.1f}% faster")
    elif improvement_pct > -5:
        print(f"⚠️  SIMILAR PERFORMANCE: {abs(improvement_pct):.1f}% difference")
    else:
        print(f"⚠️  SLOWER: {abs(improvement_pct):.1f}% overhead (expected for small files)")
    
    if result_baseline['gpu_warning'] and not result_optimized['gpu_warning']:
        print("✅ GPU WARNING ELIMINATED")
    elif result_baseline['gpu_warning'] and result_optimized['gpu_warning']:
        print("⚠️  GPU warning still present (may need GPU-accelerated model)")
    
    # Check if batch size adjustment happened
    if "Batch size adjusted" in result_optimized['stderr']:
        print("✅ Batch size optimization applied")
        for line in result_optimized['stderr'].split('\n'):
            if "Batch size adjusted" in line:
                print(f"   {line.strip()}")
    
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    
    if file_size < 50 * 1024:  # < 50KB
        print("📝 File is small. --use-datasets is most beneficial for files > 50MB")
    else:
        print("📝 File size is appropriate for --use-datasets optimization")
    
    if improvement_pct > 10:
        print("✅ RECOMMENDED: Use --use-datasets for this type of file")
    elif improvement_pct > 0:
        print("✅ OPTIONAL: Small benefit, use for GPU warning elimination")
    else:
        print("ℹ️  OPTIONAL: Use primarily to eliminate GPU warnings on large datasets")
    
    print("\nFor best results with large datasets (>100MB):")
    print("  python3 anon.py data.csv --use-datasets --csv-chunk-size 10000 --batch-size 128")

if __name__ == "__main__":
    main()
