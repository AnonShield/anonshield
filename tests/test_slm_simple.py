#!/usr/bin/env python3
"""
Simple test to verify SLM cache implementation.
Tests with a small dataset to validate cache hits/misses.
"""

import subprocess
import time
import os
import sys

def run_command(cmd, description):
    """Run command and return time elapsed."""
    print(f"\n{'='*70}")
    print(f"{description}")
    print(f"{'='*70}")
    print(f"Command: {cmd}\n")
    
    start = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    elapsed = time.time() - start
    
    if result.returncode != 0:
        print(f"❌ FAILED (exit code {result.returncode})")
        print(f"STDOUT: {result.stdout[-500:]}")
        print(f"STDERR: {result.stderr[-500:]}")
        return None, elapsed
    
    print(f"✅ SUCCESS in {elapsed:.2f}s")
    return result.stdout, elapsed

def main():
    print("="*70)
    print("Testing SLM Cache Implementation")
    print("="*70)
    
    # Check if Ollama is running
    print("\nChecking if Ollama is running...")
    result = subprocess.run("curl -s http://localhost:11434/api/tags", 
                          shell=True, capture_output=True, text=True)
    
    if result.returncode != 0 or not result.stdout.strip():
        print("❌ Ollama is NOT running!")
        print("\nTo start Ollama:")
        print("  1. In another terminal: ollama serve")
        print("  2. Wait for 'Listening on 127.0.0.1:11434'")
        print("  3. Run this test again")
        sys.exit(1)
    
    print(f"✅ Ollama is running")
    
    # Create test file with 20 lines (10 unique, repeated 2x)
    print("\nCreating test file...")
    test_content = """John Smith works at Microsoft.
María García lives in Madrid.
Email: contact@example.com
Phone: +1-555-0123
John Smith works at Microsoft.
IP Address: 192.168.1.1
María García lives in Madrid.
Credit Card: 4532-1234-5678-9010
Email: contact@example.com
Phone: +1-555-0123
John Smith works at Microsoft.
IP Address: 192.168.1.1
María García lives in Madrid.
Credit Card: 4532-1234-5678-9010
Email: contact@example.com
Phone: +1-555-0123
IP Address: 192.168.1.1
John Smith works at Microsoft.
Credit Card: 4532-1234-5678-9010
Phone: +1-555-0123
"""
    
    with open("test_slm_simple.txt", "w") as f:
        f.write(test_content)
    
    file_size = os.path.getsize("test_slm_simple.txt")
    lines = len(test_content.strip().split('\n'))
    unique_lines = len(set(test_content.strip().split('\n')))
    
    print(f"✅ Created test_slm_simple.txt:")
    print(f"   Size: {file_size} bytes")
    print(f"   Total lines: {lines}")
    print(f"   Unique lines: {unique_lines}")
    print(f"   Expected cache hit rate: {(1 - unique_lines/lines)*100:.1f}%")
    
    # Test 1: WITH cache
    stdout1, time1 = run_command(
        "python3 anon.py test_slm_simple.txt "
        "--anonymization-strategy slm "
        "--use-cache "
        "--output-dir output/slm_with_cache "
        "--no-report "
        "--overwrite "
        "--log-level INFO 2>&1 | grep -E '(Cache|SLM|Processing|unique)'",
        "Test 1: SLM WITH cache"
    )
    
    if time1 is None:
        print("\n❌ Test failed - check if Ollama model is available")
        print("Run: ollama pull llama3.2:1b")
        sys.exit(1)
    
    # Test 2: WITHOUT cache (for comparison)
    stdout2, time2 = run_command(
        "python3 anon.py test_slm_simple.txt "
        "--anonymization-strategy slm "
        "--output-dir output/slm_without_cache "
        "--no-report "
        "--overwrite "
        "--log-level INFO 2>&1 | grep -E '(Cache|SLM|Processing|unique)'",
        "Test 2: SLM WITHOUT cache"
    )
    
    # Results
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"Time WITH cache:    {time1:.2f}s")
    print(f"Time WITHOUT cache: {time2:.2f}s")
    
    if time2 > time1:
        speedup = time2 / time1
        improvement = ((time2 - time1) / time2) * 100
        print(f"Speedup:            {speedup:.2f}x")
        print(f"Improvement:        {improvement:.1f}%")
        print(f"\n✅ Cache is working! {improvement:.1f}% faster with cache")
    else:
        print(f"\n⚠️  Cache might not be effective on this small dataset")
        print(f"   Try with larger files with more repeated content")
    
    # Check for cache hits in logs
    if stdout1 and "cache" in stdout1.lower():
        print(f"\nCache activity detected in logs:")
        for line in stdout1.split('\n'):
            if 'cache' in line.lower():
                print(f"  {line}")
    
    print("\n" + "="*70)
    print("✅ SLM cache test completed!")
    print("="*70)

if __name__ == "__main__":
    main()
