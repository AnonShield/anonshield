#!/usr/bin/env python3
"""
Test: Verify batch size adapts to TEXT LENGTH in CSV cells.
Demonstrates that large JSON cells → smaller batch size.
"""

import pandas as pd
import subprocess
import os
import sys

os.environ["ANON_SECRET_KEY"] = "test-key-12345678901234567890123456789012"

print("="*70)
print("Testing: Adaptive Batch Size Based on Cell Text Length")
print("="*70)

# Test 1: CSV with SHORT cells
print("\n1️⃣  Creating CSV with SHORT cells (avg ~10 chars)...")
data_short = {
    'id': [i for i in range(100)],
    'name': [f'User{i}' for i in range(100)],
    'email': [f'user{i}@test.com' for i in range(100)]
}
df_short = pd.DataFrame(data_short)
df_short.to_csv('tests/test_data/csv_short_cells.csv', index=False)
print(f"   ✅ Created csv_short_cells.csv (3 columns, short text)")

# Test 2: CSV with LONG cells (like your CVE dataset)
print("\n2️⃣  Creating CSV with LONG cells (avg ~2000 chars, like JSON)...")
long_json = '{"vulnerability": {"cve": "CVE-2024-12345", "description": "' + 'A'*1800 + '", "severity": "critical"}'
data_long = {
    'cve_id': [f'CVE-2024-{i:05d}' for i in range(100)],
    'frequency': [i % 100 for i in range(100)],
    'cve_data': [long_json for _ in range(100)]  # Long JSON in each cell
}
df_long = pd.DataFrame(data_long)
df_long.to_csv('tests/test_data/csv_long_cells.csv', index=False)

# Calculate actual average
avg_short = sum(len(str(v)) for row in data_short.values() for v in row) / (100 * 3)
avg_long = sum(len(str(v)) for row in data_long.values() for v in row) / (100 * 3)

print(f"   ✅ Created csv_long_cells.csv (3 columns, long JSON)")
print(f"   📊 Average cell length:")
print(f"      Short CSV: {avg_short:.0f} chars")
print(f"      Long CSV:  {avg_long:.0f} chars")

# Test 3: Run with --batch-size auto on BOTH files
print("\n3️⃣  Running anonymization with --batch-size auto...")

print("\n   Testing SHORT cells CSV:")
result_short = subprocess.run(
    "python3 anon.py tests/test_data/csv_short_cells.csv --batch-size auto --no-report --overwrite --output-dir output/test_short 2>&1 | grep -E 'Adaptive batch size|avg_length|batch_size='",
    shell=True,
    capture_output=True,
    text=True,
    timeout=120
)
print("   " + result_short.stdout.replace('\n', '\n   '))

print("\n   Testing LONG cells CSV:")
result_long = subprocess.run(
    "python3 anon.py tests/test_data/csv_long_cells.csv --batch-size auto --no-report --overwrite --output-dir output/test_long 2>&1 | grep -E 'Adaptive batch size|avg_length|batch_size='",
    shell=True,
    capture_output=True,
    text=True,
    timeout=120
)
print("   " + result_long.stdout.replace('\n', '\n   '))

print("\n" + "="*70)
print("EXPECTED BEHAVIOR:")
print("="*70)
print("✅ SHORT cells (~10 chars) → LARGER batch size (e.g., 600-800)")
print("✅ LONG cells (~2000 chars) → SMALLER batch size (e.g., 150-250)")
print("\nThis prevents memory issues with large JSON/text in CSV cells.")
print("="*70)
