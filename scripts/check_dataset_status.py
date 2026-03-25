#!/usr/bin/env python3
"""
Quick Dataset Status Check

Fast overview of dataset status without full analysis.
Shows file counts and total sizes by format.

Author: AnonShield Team  
Date: February 2026
"""

import sys
from pathlib import Path
from collections import defaultdict


def format_size(bytes_size):
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def check_directory(directory: Path):
    """Quick scan of a directory."""
    if not directory.exists():
        return None
    
    stats = defaultdict(lambda: {'count': 0, 'total_bytes': 0})
    excluded = {'.anonymous', '.anon', '.bak', '.tmp', '.log'}
    
    for file_path in directory.rglob("*"):
        if not file_path.is_file():
            continue
        
        if any(suffix in file_path.suffixes for suffix in excluded):
            continue
        
        if file_path.name.startswith("."):
            continue
        
        ext = file_path.suffix.lower()
        if not ext:
            continue
        
        try:
            size = file_path.stat().st_size
            stats[ext]['count'] += 1
            stats[ext]['total_bytes'] += size
        except:
            pass
    
    return dict(stats)


def print_directory_stats(label: str, directory: Path):
    """Print statistics for a directory."""
    stats = check_directory(directory)
    
    if stats is None:
        print(f"\n{label}")
        print(f"  Status: NOT FOUND ✗")
        return
    
    if not stats:
        print(f"\n{label}")
        print(f"  Status: EMPTY (no files found)")
        return
    
    print(f"\n{label}")
    print(f"  Location: {directory}")
    
    total_files = sum(s['count'] for s in stats.values())
    total_bytes = sum(s['total_bytes'] for s in stats.values())
    
    print(f"  Total: {total_files} files, {format_size(total_bytes)}")
    print(f"  Formats: {len(stats)}")
    
    print("\n  By Format:")
    for ext in sorted(stats.keys()):
        count = stats[ext]['count']
        size = format_size(stats[ext]['total_bytes'])
        print(f"    {ext:<8} {count:>6} files, {size:>12}")


def main():
    """Main entry point."""
    print("="*70)
    print("DATASET STATUS CHECK")
    print("="*70)
    
    # Check original dataset
    print_directory_stats(
        "📁 Original Dataset",
        Path("vulnnet_scans_openvas")
    )
    
    # Check converted datasets
    base_path = Path("benchmark/converted_datasets")
    
    for format_name in ['xlsx', 'docx', 'json', 'images']:
        format_path = base_path / format_name
        print_directory_stats(
            f"📁 Converted: {format_name.upper()}",
            format_path
        )
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    all_dirs = [
        Path("vulnnet_scans_openvas"),
        base_path / "xlsx",
        base_path / "docx",
        base_path / "json",
        base_path / "images"
    ]
    
    total_files = 0
    total_bytes = 0
    existing_dirs = 0
    
    for dir_path in all_dirs:
        stats = check_directory(dir_path)
        if stats:
            existing_dirs += 1
            total_files += sum(s['count'] for s in stats.values())
            total_bytes += sum(s['total_bytes'] for s in stats.values())
    
    print(f"Directories found: {existing_dirs}/5")
    print(f"Total files: {total_files}")
    print(f"Total size: {format_size(total_bytes)}")
    
    # Recommendations
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    
    original_stats = check_directory(Path("vulnnet_scans_openvas"))
    
    if not original_stats:
        print("❌ Original dataset not found!")
        print("   Check that vulnnet_scans_openvas directory exists.")
    else:
        missing_formats = []
        for fmt in ['xlsx', 'docx', 'json', 'images']:
            if not check_directory(base_path / fmt):
                missing_formats.append(fmt)
        
        if missing_formats:
            print(f"⚠️  Missing converted formats: {', '.join(missing_formats)}")
            print("   Run: python scripts/convert_dataset.py --all")
        else:
            print("✅ All formats available!")
            print("   Run: scripts/complete_benchmark_workflow.sh")
    
    print("")


if __name__ == "__main__":
    main()
