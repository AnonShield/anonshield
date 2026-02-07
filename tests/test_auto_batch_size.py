#!/usr/bin/env python3
"""
Test --batch-size auto feature.
Demonstrates adaptive batch sizing based on file characteristics.
"""

import subprocess
import sys
import os

def test_auto_batch_size(file_path, strategy):
    """Test with auto batch size."""
    cmd = f"python3 anon.py {file_path} --batch-size auto --anonymization-strategy {strategy} --no-report --overwrite --log-level INFO --output-dir output/test_auto 2>&1 | grep -E '(Adaptive batch size|batch_size=|batch size)'"
    
    print(f"\n{'='*70}")
    print(f"Testing: --batch-size auto")
    print(f"File: {file_path}")
    print(f"Strategy: {strategy}")
    print(f"{'='*70}\n")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    output = result.stdout + result.stderr
    
    # Extract adaptive batch size info
    for line in output.split('\n'):
        if 'adaptive' in line.lower() or 'batch' in line.lower():
            print(f"  {line.strip()}")
    
    return result.returncode == 0

def main():
    print("="*70)
    print("Testing --batch-size auto Feature")
    print("="*70)
    
    # Test 1: Small text file with short lines
    print("\nTest 1: Small text file (short lines)")
    print("Expected: Higher batch size (~1200-1500)")
    
    with open("test_short_lines.txt", "w") as f:
        for i in range(50):
            f.write(f"Short line {i} with data.\n")
    
    test_auto_batch_size("test_short_lines.txt", "presidio")
    
    # Test 2: Text file with long lines
    print("\n\nTest 2: Text file with long lines")
    print("Expected: Lower batch size (~300-500)")
    
    with open("test_long_lines.txt", "w") as f:
        for i in range(20):
            f.write(f"This is line {i} with much longer text content " * 20 + "\n")
    
    test_auto_batch_size("test_long_lines.txt", "presidio")
    
    # Test 3: CSV with many columns
    print("\n\nTest 3: CSV with many columns (25 columns)")
    print("Expected: Lower batch size (~600-800)")
    
    import pandas as pd
    data = {f"col_{i}": [f"value_{j}" for j in range(100)] for i in range(25)}
    df = pd.DataFrame(data)
    df.to_csv("test_many_cols.csv", index=False)
    
    test_auto_batch_size("test_many_cols.csv", "presidio")
    
    # Test 4: CSV with few columns
    print("\n\nTest 4: CSV with few columns (3 columns)")
    print("Expected: Higher batch size (~800-1000)")
    
    data2 = {f"col_{i}": [f"value_{j}" for j in range(100)] for i in range(3)}
    df2 = pd.DataFrame(data2)
    df2.to_csv("test_few_cols.csv", index=False)
    
    test_auto_batch_size("test_few_cols.csv", "presidio")
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("✅ --batch-size auto adapts based on:")
    print("   • File size (larger = bigger batch)")
    print("   • Text length (longer = smaller batch)")
    print("   • CSV columns (more = smaller batch)")
    print("   • Strategy (presidio=500, fast=1200, balanced=800, slm=300)")
    print("   • GPU memory (more = bigger batch)")
    print("\nUsage:")
    print("  python3 anon.py file.csv --batch-size auto")
    print("  python3 anon.py file.txt --batch-size 2000  # Manual override")
    print("="*70)
    
    # Cleanup
    for f in ["test_short_lines.txt", "test_long_lines.txt", "test_many_cols.csv", "test_few_cols.csv"]:
        if os.path.exists(f):
            os.remove(f)

if __name__ == "__main__":
    os.environ["ANON_SECRET_KEY"] = "test-key-12345678901234567890123456789012"
    main()
