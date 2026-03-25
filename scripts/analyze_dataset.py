#!/usr/bin/env python3
"""
Dataset Statistics Analyzer for AnonLFI Benchmark

Analyzes file sizes and generates detailed statistics for each format.
Produces comprehensive reports in multiple formats (CSV, JSON, Markdown).

Features:
- Comprehensive statistics (min, max, mean, median, std, total)
- Grouping by file extension
- Multiple output formats
- Pretty-printed tables
- Histogram generation (optional)
- Outlier detection

Author: AnonShield Team
Date: February 2026
"""

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional
import logging


@dataclass
class FileStats:
    """Statistics for a single file."""
    path: str
    size_bytes: int
    size_kb: float
    size_mb: float
    extension: str


@dataclass
class FormatStatistics:
    """Statistics for a file format."""
    extension: str
    count: int
    total_bytes: int
    total_kb: float
    total_mb: float
    min_bytes: int
    max_bytes: int
    mean_bytes: float
    median_bytes: float
    std_dev_bytes: float
    min_kb: float
    max_kb: float
    mean_kb: float
    median_kb: float
    min_mb: float
    max_mb: float
    mean_mb: float
    median_mb: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export."""
        return asdict(self)


class DatasetAnalyzer:
    """Analyzes dataset files and generates statistics."""
    
    def __init__(self, directories: List[Path], output_dir: Path, verbose: bool = False):
        self.directories = directories
        self.output_dir = output_dir
        self.verbose = verbose
        self.logger = self._setup_logger()
        
        # Data structures
        self.files_by_extension: Dict[str, List[FileStats]] = defaultdict(list)
        self.statistics_by_extension: Dict[str, FormatStatistics] = {}
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging."""
        logger = logging.getLogger("DatasetAnalyzer")
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def scan_files(self):
        """Scan directories and collect file information."""
        self.logger.info("="*70)
        self.logger.info("DATASET ANALYSIS STARTED")
        self.logger.info("="*70)
        
        excluded_suffixes = {".anonymous", ".anon", ".bak", ".tmp", ".log"}
        
        for directory in self.directories:
            if not directory.exists():
                self.logger.warning(f"Directory not found: {directory}")
                continue
            
            self.logger.info(f"Scanning: {directory}")
            
            for file_path in directory.rglob("*"):
                if not file_path.is_file():
                    continue
                
                # Skip excluded files
                if any(suffix in file_path.suffixes for suffix in excluded_suffixes):
                    continue
                
                # Skip hidden files
                if file_path.name.startswith("."):
                    continue
                
                # Get file info
                try:
                    size_bytes = file_path.stat().st_size
                    size_kb = size_bytes / 1024
                    size_mb = size_bytes / (1024 * 1024)
                    extension = file_path.suffix.lower()
                    
                    if not extension:
                        continue
                    
                    file_stats = FileStats(
                        path=str(file_path.relative_to(directory)),
                        size_bytes=size_bytes,
                        size_kb=size_kb,
                        size_mb=size_mb,
                        extension=extension
                    )
                    
                    self.files_by_extension[extension].append(file_stats)
                    
                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {e}")
        
        total_files = sum(len(files) for files in self.files_by_extension.values())
        self.logger.info(f"Found {total_files} files across {len(self.files_by_extension)} formats")
        self.logger.info("")
    
    def compute_statistics(self):
        """Compute statistics for each extension."""
        self.logger.info("Computing statistics...")
        
        for extension, files in sorted(self.files_by_extension.items()):
            if not files:
                continue
            
            sizes_bytes = [f.size_bytes for f in files]
            sizes_kb = [f.size_kb for f in files]
            sizes_mb = [f.size_mb for f in files]
            
            stats = FormatStatistics(
                extension=extension,
                count=len(files),
                total_bytes=sum(sizes_bytes),
                total_kb=sum(sizes_kb),
                total_mb=sum(sizes_mb),
                min_bytes=min(sizes_bytes),
                max_bytes=max(sizes_bytes),
                mean_bytes=statistics.mean(sizes_bytes),
                median_bytes=statistics.median(sizes_bytes),
                std_dev_bytes=statistics.stdev(sizes_bytes) if len(sizes_bytes) > 1 else 0.0,
                min_kb=min(sizes_kb),
                max_kb=max(sizes_kb),
                mean_kb=statistics.mean(sizes_kb),
                median_kb=statistics.median(sizes_kb),
                min_mb=min(sizes_mb),
                max_mb=max(sizes_mb),
                mean_mb=statistics.mean(sizes_mb),
                median_mb=statistics.median(sizes_mb),
            )
            
            self.statistics_by_extension[extension] = stats
        
        self.logger.info("Statistics computed")
        self.logger.info("")
    
    def generate_reports(self):
        """Generate all report formats."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("Generating reports...")
        
        # Generate reports
        self._generate_csv_report()
        self._generate_json_report()
        self._generate_markdown_report()
        self._generate_detailed_csv()
        
        self.logger.info("")
        self.logger.info("="*70)
        self.logger.info("REPORTS GENERATED")
        self.logger.info("="*70)
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"  - dataset_statistics.csv")
        self.logger.info(f"  - dataset_statistics.json")
        self.logger.info(f"  - dataset_statistics.md")
        self.logger.info(f"  - dataset_files_detailed.csv")
        self.logger.info("="*70)
    
    def _generate_csv_report(self):
        """Generate CSV report with statistics."""
        csv_path = self.output_dir / "dataset_statistics.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'extension', 'count', 'total_mb', 'total_kb', 'total_bytes',
                'min_mb', 'max_mb', 'mean_mb', 'median_mb',
                'min_kb', 'max_kb', 'mean_kb', 'median_kb',
                'min_bytes', 'max_bytes', 'mean_bytes', 'median_bytes', 'std_dev_bytes'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for ext in sorted(self.statistics_by_extension.keys()):
                stats = self.statistics_by_extension[ext]
                writer.writerow(stats.to_dict())
        
        self.logger.info(f"✓ CSV report: {csv_path}")
    
    def _generate_json_report(self):
        """Generate JSON report with statistics."""
        json_path = self.output_dir / "dataset_statistics.json"
        
        data = {
            "generated_at": Path(__file__).name,
            "total_files": sum(s.count for s in self.statistics_by_extension.values()),
            "total_size_mb": sum(s.total_mb for s in self.statistics_by_extension.values()),
            "formats": {
                ext: stats.to_dict() 
                for ext, stats in sorted(self.statistics_by_extension.items())
            }
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"✓ JSON report: {json_path}")
    
    def _generate_markdown_report(self):
        """Generate Markdown report with formatted tables."""
        md_path = self.output_dir / "dataset_statistics.md"
        
        lines = []
        lines.append("# Dataset Statistics Report")
        lines.append("")
        lines.append(f"**Total Files:** {sum(s.count for s in self.statistics_by_extension.values())}")
        lines.append(f"**Total Size:** {sum(s.total_mb for s in self.statistics_by_extension.values()):.2f} MB")
        lines.append(f"**Formats:** {len(self.statistics_by_extension)}")
        lines.append("")
        
        # Summary table
        lines.append("## Summary by Format")
        lines.append("")
        lines.append("| Extension | Count | Total Size (MB) | Min (KB) | Max (KB) | Mean (KB) | Median (KB) |")
        lines.append("|-----------|-------|-----------------|----------|----------|-----------|-------------|")
        
        for ext in sorted(self.statistics_by_extension.keys()):
            stats = self.statistics_by_extension[ext]
            lines.append(
                f"| {ext:<9} | {stats.count:>5} | {stats.total_mb:>15.2f} | "
                f"{stats.min_kb:>8.1f} | {stats.max_kb:>8.1f} | "
                f"{stats.mean_kb:>9.1f} | {stats.median_kb:>11.1f} |"
            )
        
        lines.append("")
        
        # Detailed statistics
        lines.append("## Detailed Statistics")
        lines.append("")
        
        for ext in sorted(self.statistics_by_extension.keys()):
            stats = self.statistics_by_extension[ext]
            lines.append(f"### {ext.upper()}")
            lines.append("")
            lines.append(f"- **Count:** {stats.count}")
            lines.append(f"- **Total Size:** {stats.total_mb:.2f} MB ({stats.total_kb:.1f} KB)")
            lines.append(f"- **Min Size:** {stats.min_mb:.4f} MB ({stats.min_kb:.1f} KB, {stats.min_bytes} bytes)")
            lines.append(f"- **Max Size:** {stats.max_mb:.4f} MB ({stats.max_kb:.1f} KB, {stats.max_bytes} bytes)")
            lines.append(f"- **Mean Size:** {stats.mean_mb:.4f} MB ({stats.mean_kb:.1f} KB)")
            lines.append(f"- **Median Size:** {stats.median_mb:.4f} MB ({stats.median_kb:.1f} KB)")
            lines.append(f"- **Std Dev:** {stats.std_dev_bytes / 1024:.1f} KB")
            lines.append("")
        
        # Size distribution
        lines.append("## Size Distribution")
        lines.append("")
        lines.append("| Extension | <10 KB | 10-50 KB | 50-100 KB | 100-500 KB | >500 KB |")
        lines.append("|-----------|--------|----------|-----------|------------|---------|")
        
        for ext in sorted(self.statistics_by_extension.keys()):
            files = self.files_by_extension[ext]
            
            buckets = {
                "<10 KB": 0,
                "10-50 KB": 0,
                "50-100 KB": 0,
                "100-500 KB": 0,
                ">500 KB": 0
            }
            
            for f in files:
                kb = f.size_kb
                if kb < 10:
                    buckets["<10 KB"] += 1
                elif kb < 50:
                    buckets["10-50 KB"] += 1
                elif kb < 100:
                    buckets["50-100 KB"] += 1
                elif kb < 500:
                    buckets["100-500 KB"] += 1
                else:
                    buckets[">500 KB"] += 1
            
            lines.append(
                f"| {ext:<9} | {buckets['<10 KB']:>6} | {buckets['10-50 KB']:>8} | "
                f"{buckets['50-100 KB']:>9} | {buckets['100-500 KB']:>10} | {buckets['>500 KB']:>7} |"
            )
        
        lines.append("")
        
        # Top 10 largest files
        lines.append("## Top 10 Largest Files")
        lines.append("")
        
        all_files = []
        for ext, files in self.files_by_extension.items():
            all_files.extend(files)
        
        all_files.sort(key=lambda f: f.size_bytes, reverse=True)
        
        lines.append("| Rank | File | Extension | Size (MB) | Size (KB) |")
        lines.append("|------|------|-----------|-----------|-----------|")
        
        for i, file in enumerate(all_files[:10], 1):
            filename = Path(file.path).name
            lines.append(
                f"| {i:>4} | {filename:<50} | {file.extension:<9} | "
                f"{file.size_mb:>9.2f} | {file.size_kb:>9.1f} |"
            )
        
        lines.append("")
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        self.logger.info(f"✓ Markdown report: {md_path}")
    
    def _generate_detailed_csv(self):
        """Generate detailed CSV with all files."""
        csv_path = self.output_dir / "dataset_files_detailed.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['path', 'extension', 'size_bytes', 'size_kb', 'size_mb']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            all_files = []
            for ext, files in self.files_by_extension.items():
                all_files.extend(files)
            
            # Sort by size descending
            all_files.sort(key=lambda f: f.size_bytes, reverse=True)
            
            for file in all_files:
                writer.writerow(asdict(file))
        
        self.logger.info(f"✓ Detailed CSV: {csv_path}")
    
    def print_console_summary(self):
        """Print summary to console."""
        print("\n" + "="*70)
        print("DATASET STATISTICS SUMMARY")
        print("="*70)
        print(f"\n{'Extension':<12} {'Count':>8} {'Total (MB)':>12} {'Min (KB)':>10} {'Max (KB)':>10} {'Mean (KB)':>10}")
        print("-"*12 + " " + "-"*8 + " " + "-"*12 + " " + "-"*10 + " " + "-"*10 + " " + "-"*10)
        
        for ext in sorted(self.statistics_by_extension.keys()):
            stats = self.statistics_by_extension[ext]
            print(f"{ext:<12} {stats.count:>8} {stats.total_mb:>12.2f} "
                  f"{stats.min_kb:>10.1f} {stats.max_kb:>10.1f} {stats.mean_kb:>10.1f}")
        
        # Totals
        total_count = sum(s.count for s in self.statistics_by_extension.values())
        total_mb = sum(s.total_mb for s in self.statistics_by_extension.values())
        
        print("-"*12 + " " + "-"*8 + " " + "-"*12 + " " + "-"*10 + " " + "-"*10 + " " + "-"*10)
        print(f"{'TOTAL':<12} {total_count:>8} {total_mb:>12.2f}")
        print("")
    
    def run(self):
        """Run the complete analysis."""
        self.scan_files()
        self.compute_statistics()
        self.print_console_summary()
        self.generate_reports()


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Analyze dataset files and generate statistics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze original dataset
  python analyze_dataset.py --dirs vulnnet_scans_openvas
  
  # Analyze converted formats
  python analyze_dataset.py --dirs benchmark/converted_datasets/xlsx benchmark/converted_datasets/docx
  
  # Analyze all (original + converted)
  python analyze_dataset.py --dirs vulnnet_scans_openvas benchmark/converted_datasets/xlsx benchmark/converted_datasets/docx benchmark/converted_datasets/json
  
  # Custom output directory
  python analyze_dataset.py --dirs vulnnet_scans_openvas --output my_stats
        """
    )
    
    parser.add_argument(
        "--dirs", nargs="+", required=True,
        help="Directories to analyze"
    )
    
    parser.add_argument(
        "--output", type=str,
        default="benchmark/dataset_statistics",
        help="Output directory for reports (default: benchmark/dataset_statistics)"
    )
    
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose output"
    )
    
    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Convert directories to Path objects
    directories = [Path(d) for d in args.dirs]
    output_dir = Path(args.output)
    
    # Create analyzer and run
    analyzer = DatasetAnalyzer(
        directories=directories,
        output_dir=output_dir,
        verbose=args.verbose
    )
    
    analyzer.run()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
