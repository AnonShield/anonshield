#!/usr/bin/env python3
"""
Consolidate all analysis reports and PDFs into single files.
"""
import os
from pathlib import Path
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io

def create_title_page(title_text):
    """Create a PDF title page with the given text."""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    
    # Split long text into multiple lines
    max_width = letter[0] - 40  # 20px margin on each side
    font_size = 14
    font_name = "Helvetica-Bold"
    
    # Function to wrap text
    def wrap_text(text, max_width, font_name, font_size):
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            width = can.stringWidth(test_line, font_name, font_size)
            
            if width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    # Wrap the title text
    lines = wrap_text(title_text, max_width, font_name, font_size)
    
    # Calculate starting Y position (centered vertically)
    line_height = font_size + 4
    total_height = len(lines) * line_height
    y_start = (letter[1] + total_height) / 2
    
    # Draw each line centered
    can.setFont(font_name, font_size)
    for i, line in enumerate(lines):
        text_width = can.stringWidth(line, font_name, font_size)
        x = (letter[0] - text_width) / 2
        y = y_start - (i * line_height)
        can.drawString(x, y, line)
    
    can.save()
    
    packet.seek(0)
    return packet

def consolidate_text_reports(session_dir, output_file):
    """Consolidate all text reports into a single file."""
    session_path = Path(session_dir)
    
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write("=" * 100 + "\n")
        outfile.write("CONSOLIDATED BENCHMARK ANALYSIS REPORTS\n")
        outfile.write("Session: session_20260208_005447\n")
        outfile.write("=" * 100 + "\n\n")
        
        # Find all complete_analysis_report.txt files (including subdirectories)
        report_files = sorted(session_path.glob("**/complete_analysis_report.txt"))
        
        for report_file in report_files:
            # Get relative path from session directory
            relative_path = report_file.relative_to(session_path)
            
            outfile.write("\n" + "=" * 100 + "\n")
            outfile.write(f"REPORT: {relative_path}\n")
            outfile.write("=" * 100 + "\n\n")
            
            # Read and write the report content
            with open(report_file, 'r', encoding='utf-8') as infile:
                content = infile.read()
                outfile.write(content)
            
            outfile.write("\n\n")
    
    print(f"✅ Text reports consolidated: {output_file}")
    print(f"   Combined {len(report_files)} reports")

def consolidate_pdfs(session_dir, output_file):
    """Consolidate all PDFs into a single file with title pages."""
    session_path = Path(session_dir)
    
    # Find all complete_analysis_figures.pdf files (including subdirectories)
    pdf_files = sorted(session_path.glob("**/complete_analysis_figures.pdf"))
    
    merger = PdfMerger()
    
    # Add overall title page
    title_packet = create_title_page("CONSOLIDATED BENCHMARK ANALYSIS FIGURES")
    merger.append(title_packet)
    
    for pdf_file in pdf_files:
        # Get relative path from session directory
        relative_path = pdf_file.relative_to(session_path)
        
        # Skip empty files
        if pdf_file.stat().st_size == 0:
            print(f"   ⚠️  Skipped (empty): {relative_path}")
            continue
        
        try:
            # Create title page for this section
            title_text = f"Source: {relative_path}"
            title_packet = create_title_page(title_text)
            merger.append(title_packet)
            
            # Add the actual PDF
            merger.append(str(pdf_file))
            
            print(f"   ✓ Added: {relative_path}")
        except Exception as e:
            print(f"   ❌ Error with {relative_path}: {e}")
            continue
    
    # Write the consolidated PDF
    merger.write(output_file)
    merger.close()
    
    print(f"✅ PDFs consolidated: {output_file}")
    print(f"   Combined {len(pdf_files)} PDF files")

def main():
    # Session directory
    session_dir = "/home/kapelinski/Documents/tool/benchmark/orchestrated_results/session_20260208_005447"
    
    # Output files
    output_txt = os.path.join(session_dir, "CONSOLIDATED_ALL_REPORTS.txt")
    output_pdf = os.path.join(session_dir, "CONSOLIDATED_ALL_FIGURES.pdf")
    
    print("🔄 Starting consolidation...\n")
    
    # Consolidate text reports
    consolidate_text_reports(session_dir, output_txt)
    print()
    
    # Consolidate PDFs
    print("🔄 Consolidating PDFs...")
    consolidate_pdfs(session_dir, output_pdf)
    
    print("\n✨ CONSOLIDATION COMPLETE!")
    print(f"\n📄 Text Report: {output_txt}")
    print(f"📊 PDF Figures: {output_pdf}")

if __name__ == "__main__":
    main()
