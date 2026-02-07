#!/usr/bin/env python3
"""
Test script to validate cache implementation in SLM strategy.
Measures cache hit rate and performance improvement.
"""
import os
import sys
import time
import subprocess

GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
RED = '\033[0;31m'
NC = '\033[0m'

def create_test_file_with_repetition():
    """Create a test file with highly repetitive data to maximize cache benefit"""
    print(f"{BLUE}Creating test file with repetitive data...{NC}")
    
    test_data = [
        "John Smith works at Acme Corporation.",
        "Contact email: john.smith@acme.com",
        "Phone: +1-555-0123",
        "Address: 123 Main Street, San Francisco, CA 94102",
        "John Smith works at Acme Corporation.",  # Duplicate
        "Contact email: john.smith@acme.com",     # Duplicate
        "Jane Doe also works at Acme Corporation.",
        "Her email is jane.doe@acme.com",
        "John Smith works at Acme Corporation.",  # Duplicate again
        "Phone: +1-555-0123",                      # Duplicate
    ] * 50  # Multiply to create 500 lines with heavy repetition
    
    with open("test_slm_cache.txt", "w") as f:
        f.write("\n".join(test_data))
    
    file_size = os.path.getsize("test_slm_cache.txt")
    unique_lines = len(set(test_data))
    total_lines = len(test_data)
    
    print(f"{GREEN}✅ Created test file:{NC}")
    print(f"   Size: {file_size} bytes ({file_size/1024:.2f} KB)")
    print(f"   Total lines: {total_lines}")
    print(f"   Unique lines: {unique_lines}")
    print(f"   Repetition factor: {total_lines/unique_lines:.1f}x")
    print(f"   Expected cache hits: {(total_lines-unique_lines)/total_lines*100:.1f}%")
    
    return "test_slm_cache.txt"

def run_test(test_file, use_cache, output_dir):
    """Run anonymization and capture timing + logs"""
    cache_flag = "--use-cache" if use_cache else "--no-use-cache"
    
    cmd = f"python3 anon.py {test_file} {cache_flag} --anonymization-strategy slm --output-dir {output_dir} --no-report --overwrite --log-level INFO"
    
    print(f"\n{BLUE}Running: {cmd}{NC}\n")
    
    start = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    elapsed = time.time() - start
    
    # Parse logs for cache statistics
    cache_hits = 0
    processing_count = 0
    
    for line in result.stderr.split('\n'):
        if "Cache hit" in line:
            cache_hits += 1
        if "SLM processing:" in line:
            # Extract numbers like "SLM processing: 10 texts (cache hits: 490/500 = 98.0%)"
            import re
            match = re.search(r'cache hits: (\d+)/(\d+)', line)
            if match:
                cache_hits = int(match.group(1))
                total = int(match.group(2))
                processing_count = total - cache_hits
    
    return {
        'elapsed': elapsed,
        'exit_code': result.returncode,
        'cache_hits': cache_hits,
        'processing_count': processing_count,
        'stderr': result.stderr,
        'stdout': result.stdout
    }

def main():
    print("="*70)
    print(f"{BLUE}Testing Cache Implementation in SLM Strategy{NC}")
    print("="*70)
    
    # Check prerequisites
    if not os.environ.get('ANON_SECRET_KEY'):
        os.environ['ANON_SECRET_KEY'] = 'test-key-12345678901234567890123456789012'
        print(f"{YELLOW}Set ANON_SECRET_KEY for testing{NC}")
    
    # Create test file
    test_file = create_test_file_with_repetition()
    
    # Test 1: WITH cache (should be much faster on repetitive data)
    print("\n" + "="*70)
    print(f"{GREEN}TEST 1: SLM with CACHE enabled (--use-cache){NC}")
    print("="*70)
    
    result_with_cache = run_test(test_file, use_cache=True, output_dir="output/slm_with_cache")
    
    if result_with_cache['exit_code'] == 0:
        print(f"{GREEN}✅ Success{NC}")
        print(f"   Time: {result_with_cache['elapsed']:.2f}s")
        print(f"   Cache hits: {result_with_cache['cache_hits']}")
        print(f"   Processed via SLM: {result_with_cache['processing_count']}")
    else:
        print(f"{RED}❌ Failed with exit code {result_with_cache['exit_code']}{NC}")
        print("Stderr (last 500 chars):")
        print(result_with_cache['stderr'][-500:])
        return
    
    # Test 2: WITHOUT cache (baseline - everything goes through SLM)
    print("\n" + "="*70)
    print(f"{YELLOW}TEST 2: SLM WITHOUT cache (--no-use-cache){NC}")
    print("="*70)
    
    result_without_cache = run_test(test_file, use_cache=False, output_dir="output/slm_no_cache")
    
    if result_without_cache['exit_code'] == 0:
        print(f"{GREEN}✅ Success{NC}")
        print(f"   Time: {result_without_cache['elapsed']:.2f}s")
        print(f"   Cache hits: {result_without_cache['cache_hits']}")
        print(f"   Processed via SLM: All texts (no cache)")
    else:
        print(f"{RED}❌ Failed with exit code {result_without_cache['exit_code']}{NC}")
        print("Stderr (last 500 chars):")
        print(result_without_cache['stderr'][-500:])
        return
    
    # Analysis
    print("\n" + "="*70)
    print(f"{BLUE}CACHE PERFORMANCE ANALYSIS{NC}")
    print("="*70)
    
    time_with = result_with_cache['elapsed']
    time_without = result_without_cache['elapsed']
    
    speedup = time_without / time_with if time_with > 0 else 0
    improvement_pct = ((time_without - time_with) / time_without * 100) if time_without > 0 else 0
    
    print(f"\n{'Metric':<35} {'With Cache':<20} {'Without Cache':<20}")
    print("-" * 75)
    print(f"{'Execution time':<35} {time_with:>15.2f}s    {time_without:>15.2f}s")
    print(f"{'Cache hits':<35} {result_with_cache['cache_hits']:>15}    {result_without_cache['cache_hits']:>15}")
    print(f"{'SLM API calls':<35} {result_with_cache['processing_count']:>15}    {'All':>15}")
    
    print(f"\n{BLUE}Performance Gain:{NC}")
    print(f"  Speedup: {speedup:.2f}x")
    print(f"  Time saved: {time_without - time_with:.2f}s ({improvement_pct:.1f}%)")
    
    # Verify outputs are the same
    print(f"\n{BLUE}Verifying output consistency...{NC}")
    from pathlib import Path
    
    file_with = Path("output/slm_with_cache") / f"anon_{test_file}"
    file_without = Path("output/slm_no_cache") / f"anon_{test_file}"
    
    if file_with.exists() and file_without.exists():
        with open(file_with, 'r') as f1, open(file_without, 'r') as f2:
            content_with = f1.read()
            content_without = f2.read()
        
        if content_with == content_without:
            print(f"{GREEN}✅ Outputs are identical (correctness verified){NC}")
        else:
            print(f"{YELLOW}⚠️  Outputs differ (may be due to SLM variability){NC}")
    
    # Summary
    print("\n" + "="*70)
    print(f"{BLUE}SUMMARY{NC}")
    print("="*70)
    
    if speedup > 2:
        print(f"{GREEN}✅ EXCELLENT: Cache provides {speedup:.1f}x speedup!{NC}")
        print(f"{GREEN}   Cache is working perfectly for repetitive data.{NC}")
    elif speedup > 1.5:
        print(f"{GREEN}✅ GOOD: Cache provides {speedup:.1f}x speedup{NC}")
        print(f"{GREEN}   Cache is working well.{NC}")
    elif speedup > 1.1:
        print(f"{YELLOW}⚠️ MODEST: Cache provides {speedup:.1f}x speedup{NC}")
        print(f"{YELLOW}   Cache is working but benefit is limited.{NC}")
    else:
        print(f"{RED}❌ MINIMAL: Cache provides only {speedup:.1f}x speedup{NC}")
        print(f"{RED}   Cache may not be working properly.{NC}")
    
    print(f"\n{BLUE}Recommendation:{NC}")
    if speedup > 2:
        print(f"  Always use --use-cache with SLM strategy for repetitive data!")
    else:
        print(f"  Cache benefit is limited. Consider other strategies for better performance.")
    
    # Cleanup
    print(f"\n{BLUE}Test files can be found in:{NC}")
    print(f"  Input: {test_file}")
    print(f"  Output (cached): output/slm_with_cache/anon_{test_file}")
    print(f"  Output (uncached): output/slm_no_cache/anon_{test_file}")

if __name__ == "__main__":
    main()
