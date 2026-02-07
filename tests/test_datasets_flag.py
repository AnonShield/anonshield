#!/usr/bin/env python3
"""
Test script to validate --use-datasets flag and measure performance improvement.
This script compares processing time with and without the flag.
"""
import os
import sys
import time
import subprocess
import json
from pathlib import Path

# Colors for output
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
RED = '\033[0;31m'
NC = '\033[0m'  # No Color

def run_command(cmd, capture_warning=False):
    """Run command and return time, exit code, and optionally check for GPU warning"""
    start = time.time()
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    elapsed = time.time() - start
    
    gpu_warning_found = False
    if capture_warning and result.stderr:
        gpu_warning_found = "pipelines sequentially on GPU" in result.stderr
    
    return elapsed, result.returncode, gpu_warning_found, result.stderr

def print_header(text):
    print(f"\n{BLUE}{'='*70}{NC}")
    print(f"{BLUE}{text:^70}{NC}")
    print(f"{BLUE}{'='*70}{NC}\n")

def print_result(label, value, color=GREEN):
    print(f"{color}{label:.<50} {value}{NC}")

def main():
    print_header("Testing --use-datasets Flag Performance")
    
    # Check if we're in the right directory
    if not os.path.exists('anon.py'):
        print(f"{RED}Error: anon.py not found. Run this script from the tool directory.{NC}")
        sys.exit(1)
    
    # Check for test file
    test_file = "test_dedup.txt"
    if not os.path.exists(test_file):
        print(f"{YELLOW}Creating test file: {test_file}{NC}")
        with open(test_file, 'w') as f:
            f.write("John Smith works at Acme Corp\n" * 100)
            f.write("Jane Doe is from Brazil\n" * 100)
            f.write("Contact: john@example.com\n" * 50)
    
    # Check if secret key is set
    if not os.environ.get('ANON_SECRET_KEY'):
        os.environ['ANON_SECRET_KEY'] = 'test-key-12345678901234567890123456789012'
        print(f"{YELLOW}Set ANON_SECRET_KEY for testing{NC}")
    
    output_dir_without = "output/test_without_datasets"
    output_dir_with = "output/test_with_datasets"
    
    # Clean up previous outputs
    for out_dir in [output_dir_without, output_dir_with]:
        if os.path.exists(out_dir):
            subprocess.run(f"rm -rf {out_dir}", shell=True)
    
    print(f"{GREEN}Test file:{NC} {test_file}")
    file_size = os.path.getsize(test_file)
    print(f"{GREEN}File size:{NC} {file_size} bytes ({file_size/1024:.2f} KB)\n")
    
    # Base command
    base_cmd = f"python3 anon.py {test_file} --no-report --overwrite --log-level WARNING"
    
    # Test 1: Without --use-datasets
    print_header("Test 1: WITHOUT --use-datasets (baseline)")
    cmd_without = f"{base_cmd} --output-dir {output_dir_without}"
    print(f"Command: {cmd_without}\n")
    
    time_without, exit_code_without, warning_without, stderr_without = run_command(cmd_without, capture_warning=True)
    
    if exit_code_without != 0:
        print(f"{RED}❌ Test failed with exit code {exit_code_without}{NC}")
        print(f"{RED}Error output:{NC}")
        print(stderr_without[-500:] if len(stderr_without) > 500 else stderr_without)
    else:
        print(f"{GREEN}✅ Test completed successfully{NC}")
    
    print_result("Time elapsed", f"{time_without:.3f}s")
    print_result("GPU warning found", "YES" if warning_without else "NO", RED if warning_without else GREEN)
    
    # Test 2: With --use-datasets
    print_header("Test 2: WITH --use-datasets (optimized)")
    cmd_with = f"{base_cmd} --output-dir {output_dir_with} --use-datasets"
    print(f"Command: {cmd_with}\n")
    
    time_with, exit_code_with, warning_with, stderr_with = run_command(cmd_with, capture_warning=True)
    
    if exit_code_with != 0:
        print(f"{RED}❌ Test failed with exit code {exit_code_with}{NC}")
        print(f"{RED}Error output:{NC}")
        print(stderr_with[-500:] if len(stderr_with) > 500 else stderr_with)
    else:
        print(f"{GREEN}✅ Test completed successfully{NC}")
    
    print_result("Time elapsed", f"{time_with:.3f}s")
    print_result("GPU warning found", "YES" if warning_with else "NO", RED if warning_with else GREEN)
    
    # Calculate improvement
    print_header("Performance Comparison")
    
    if exit_code_without == 0 and exit_code_with == 0:
        speedup = time_without / time_with if time_with > 0 else 0
        improvement_pct = ((time_without - time_with) / time_without * 100) if time_without > 0 else 0
        
        print_result("Baseline time (without)", f"{time_without:.3f}s", BLUE)
        print_result("Optimized time (with)", f"{time_with:.3f}s", BLUE)
        print_result("Time saved", f"{time_without - time_with:.3f}s", GREEN)
        print_result("Speedup factor", f"{speedup:.2f}x", GREEN)
        print_result("Improvement", f"{improvement_pct:.1f}%", GREEN)
        
        # Check warning elimination
        if warning_without and not warning_with:
            print(f"\n{GREEN}✅ GPU warning successfully eliminated!{NC}")
        elif warning_without and warning_with:
            print(f"\n{YELLOW}⚠️  GPU warning still present (may need larger files to see effect){NC}")
        
        # Verify outputs are consistent
        print(f"\n{BLUE}Verifying output consistency...{NC}")
        file_without = Path(output_dir_without) / f"anon_{test_file}"
        file_with = Path(output_dir_with) / f"anon_{test_file}"
        
        if file_without.exists() and file_with.exists():
            with open(file_without, 'r') as f1, open(file_with, 'r') as f2:
                content_without = f1.read()
                content_with = f2.read()
                
            if content_without == content_with:
                print(f"{GREEN}✅ Output files are identical (correctness verified){NC}")
            else:
                print(f"{YELLOW}⚠️  Output files differ (expected if different random seeds){NC}")
                # Count entities to ensure same level of anonymization
                entities_without = content_without.count('[')
                entities_with = content_with.count('[')
                print(f"   Entities in baseline: {entities_without}")
                print(f"   Entities in optimized: {entities_with}")
        
        # Summary
        print_header("Summary")
        if improvement_pct > 0:
            print(f"{GREEN}✅ --use-datasets flag provides {improvement_pct:.1f}% improvement{NC}")
            print(f"{GREEN}   Recommended for files > 50MB or with repetitive data{NC}")
        elif improvement_pct < 0:
            print(f"{YELLOW}⚠️  Overhead of {abs(improvement_pct):.1f}% detected{NC}")
            print(f"{YELLOW}   Flag is more beneficial for larger files (>50MB){NC}")
        else:
            print(f"{BLUE}ℹ️  Performance similar (use flag for GPU warning elimination){NC}")
        
        # Save results
        results = {
            "test_file": test_file,
            "file_size_bytes": file_size,
            "time_without_datasets": time_without,
            "time_with_datasets": time_with,
            "speedup": speedup,
            "improvement_pct": improvement_pct,
            "gpu_warning_without": warning_without,
            "gpu_warning_with": warning_with,
        }
        
        with open("test_datasets_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n{BLUE}Results saved to: test_datasets_results.json{NC}")
        
    else:
        print(f"{RED}Cannot compare - one or both tests failed{NC}")
        sys.exit(1)

if __name__ == "__main__":
    main()
