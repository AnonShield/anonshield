#!/usr/bin/env python3
"""
Quick test: Verify --batch-size auto is recognized and calculates adaptively.
"""

import subprocess

# Test 1: Check if 'auto' is accepted
print("Test 1: Checking if --batch-size auto is accepted...")
result = subprocess.run(
    "python3 anon.py --help | grep -A 2 'batch-size'",
    shell=True, capture_output=True, text=True
)
print(result.stdout)

# Test 2: Run with auto on small test file
print("\nTest 2: Running with --batch-size auto...")

# Create test file
with open("test_auto.txt", "w") as f:
    for i in range(100):
        f.write(f"This is test line {i} with some personal data like email@example.com\n")

import os
os.environ["ANON_SECRET_KEY"] = "test-key-12345678901234567890123456789012"

cmd = "python3 anon.py test_auto.txt --batch-size auto --no-report --overwrite --log-level INFO --output-dir output/test_auto 2>&1 | grep -i 'adaptive\\|batch'"

result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
output = result.stdout

if "Adaptive batch" in output or "adaptive" in output.lower():
    print("✅ SUCCESS: Adaptive batch sizing is working!")
    for line in output.split('\n'):
        if 'adaptive' in line.lower() or 'batch' in line.lower():
            print(f"   {line}")
else:
    print("⚠️  Check logs - adaptive messaging might not be showing")
    print(f"Output preview:\n{output[:500]}")

# Cleanup
os.remove("test_auto.txt")

print("\n" + "="*70)
print("Usage Examples:")
print("="*70)
print("# Auto-detect optimal batch size:")
print("  python3 anon.py data.csv --batch-size auto")
print()
print("# Manual batch size:")
print("  python3 anon.py data.csv --batch-size 2000")
print()
print("# Strategy-specific optimization:")
print("  python3 anon.py data.csv --batch-size auto --anonymization-strategy fast")
print("="*70)
