#!/usr/bin/env python3
"""
Quick test to verify PDF and DOCX deduplication optimization.
"""
import time
import os
import sys

# Test with a sample file
test_files = [
    "test_dedup.txt",
    # Add PDF/DOCX files if available
]

for test_file in test_files:
    if not os.path.exists(test_file):
        print(f"Skipping {test_file} - file not found")
        continue
    
    print(f"\n{'='*60}")
    print(f"Testing: {test_file}")
    print(f"{'='*60}")
    
    start = time.time()
    os.system(f'python3 anon.py {test_file} --output-dir output/test_opt --no-report --log-level DEBUG 2>&1 | grep -E "(deduplication|Anonymizing.*unique)"')
    elapsed = time.time() - start
    
    print(f"Time elapsed: {elapsed:.2f}s")

print("\n✅ Optimization test complete!")
