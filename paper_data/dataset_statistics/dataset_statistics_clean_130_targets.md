# Dataset Statistics Report (Separated PDF Types)

**Total Files:** 1040
**Total Size:** 1639.54 MB
**Formats:** 8 (PDFs separated by type)

## Summary by Format

| Extension | Type | Count | Total Size (MB) | Min (KB) | Max (KB) | Mean (KB) | Median (KB) |
|-----------|------|-------|-----------------|----------|----------|-----------|-------------|
| .csv       | Original |   130 |            9.29 |      5.5 |    750.4 |      73.2 |        30.6 |
| .txt       | Original |   130 |           11.61 |      6.9 |    975.5 |      91.5 |        33.5 |
| .xml       | Original |   130 |           34.11 |     20.6 |   1926.2 |     268.7 |       205.2 |
| .pdf       | **Original (Text)** |   130 |           33.32 |    111.3 |   1796.3 |     262.4 |       167.3 |
| .xlsx      | Converted |   130 |            3.34 |      7.9 |    224.2 |      26.3 |        15.3 |
| .docx      | Converted |   130 |            7.58 |     39.0 |    291.0 |      59.7 |        46.3 |
| .json      | Converted |   130 |           60.72 |     31.5 |   3757.8 |     478.3 |       317.4 |
| .pdf (img) | **Images (OCR)** |   130 |         1479.56 |    667.8 | 126100.7 |   11654.4 |      4267.4 |

## Key Differences: Original PDFs vs PDF Images

| Metric | Original PDFs (Text) | PDF Images (OCR) | Difference |
|--------|---------------------|------------------|------------|
| Count | 130 | 130 | Same |
| Total Size | 33.32 MB | 1479.56 MB | **44.4× larger** |
| Mean Size | 262.4 KB | 11654.4 KB | **44.4× larger** |
| Median Size | 167.3 KB | 4267.4 KB | **25.5× larger** |
| Min Size | 111.3 KB | 667.8 KB | 6.0× larger |
| Max Size | 1796.3 KB | 126100.7 KB | 70.2× larger |

**Observation:** PDF images are approximately **44× larger** on average due to storing rasterized page images instead of text. This is expected behavior for testing OCR capabilities.

## Detailed Statistics

### Original Formats

#### CSV Files
- **Count:** 130
- **Total Size:** 9.29 MB (9516.5 KB)
- **Min Size:** 0.0054 MB (5.5 KB)
- **Max Size:** 0.7328 MB (750.4 KB)
- **Mean Size:** 0.0715 MB (73.2 KB)
- **Median Size:** 0.0299 MB (30.6 KB)
- **Std Dev:** 126.5 KB

#### TXT Files
- **Count:** 130
- **Total Size:** 11.61 MB (11889.7 KB)
- **Min Size:** 0.0068 MB (6.9 KB)
- **Max Size:** 0.9527 MB (975.5 KB)
- **Mean Size:** 0.0893 MB (91.5 KB)
- **Median Size:** 0.0327 MB (33.5 KB)
- **Std Dev:** 160.0 KB

#### XML Files
- **Count:** 130
- **Total Size:** 34.11 MB (34931.0 KB)
- **Min Size:** 0.0201 MB (20.6 KB)
- **Max Size:** 1.8811 MB (1926.2 KB)
- **Mean Size:** 0.2624 MB (268.7 KB)
- **Median Size:** 0.2004 MB (205.2 KB)
- **Std Dev:** 315.5 KB

#### PDF Files (Original - Text-based)
- **Count:** 130
- **Total Size:** 33.32 MB (34114.7 KB)
- **Min Size:** 0.1087 MB (111.3 KB)
- **Max Size:** 1.7542 MB (1796.3 KB)
- **Mean Size:** 0.2563 MB (262.4 KB)
- **Median Size:** 0.1634 MB (167.3 KB)
- **Std Dev:** 274.8 KB
- **Purpose:** Standard text-based PDFs for baseline testing

### Converted Formats

#### XLSX Files (from CSV)
- **Count:** 130
- **Total Size:** 3.34 MB (3423.4 KB)
- **Min Size:** 0.0078 MB (7.9 KB)
- **Max Size:** 0.2189 MB (224.2 KB)
- **Mean Size:** 0.0257 MB (26.3 KB)
- **Median Size:** 0.0150 MB (15.3 KB)
- **Std Dev:** 33.1 KB
- **Conversion:** CSV → Excel with formatting

#### DOCX Files (from TXT)
- **Count:** 130
- **Total Size:** 7.58 MB (7762.4 KB)
- **Min Size:** 0.0380 MB (39.0 KB)
- **Max Size:** 0.2842 MB (291.0 KB)
- **Mean Size:** 0.0583 MB (59.7 KB)
- **Median Size:** 0.0452 MB (46.3 KB)
- **Std Dev:** 38.9 KB
- **Conversion:** TXT → Word document with tables

#### JSON Files (from XML)
- **Count:** 130
- **Total Size:** 60.72 MB (62180.5 KB)
- **Min Size:** 0.0307 MB (31.5 KB)
- **Max Size:** 3.6697 MB (3757.8 KB)
- **Mean Size:** 0.4671 MB (478.3 KB)
- **Median Size:** 0.3099 MB (317.4 KB)
- **Std Dev:** 629.6 KB
- **Conversion:** XML → JSON structure

#### PDF Files (Images - for OCR Testing)
- **Count:** 130
- **Total Size:** 1479.56 MB (1515071.8 KB)
- **Min Size:** 0.6522 MB (667.8 KB)
- **Max Size:** 123.1452 MB (126100.7 KB)
- **Mean Size:** 11.3812 MB (11654.4 KB)
- **Median Size:** 4.1673 MB (4267.4 KB)
- **Std Dev:** 20604.4 KB
- **Conversion:** PDF text → Images → PDF images
- **Purpose:** Testing OCR capabilities of v2.0 and v3.0

## Size Distribution

### Original PDFs (Text)

| Size Range | Count | Percentage |
|------------|-------|------------|
| <10 KB       |     0 |      0.0%  |
| 10-50 KB     |     0 |      0.0%  |
| 50-100 KB    |     0 |      0.0%  |
| 100-500 KB   |   120 |     92.3%  |
| >500 KB      |    10 |      7.7%  |

### PDF Images (OCR)

| Size Range | Count | Percentage |
|------------|-------|------------|
| <1 MB     |    22 |     16.9%  |
| 1-5 MB    |    49 |     37.7%  |
| 5-10 MB   |    16 |     12.3%  |
| 10-50 MB  |    35 |     26.9%  |
| >50 MB    |     8 |      6.2%  |

## Top 10 Largest Files

### PDF Images (Converted)

| Rank | File | Size (MB) |
|------|------|-----------|
|    1 | openvas_tleemcjr_metasploitable2_images.pdf                        |    123.15 |
|    2 | openvas_ianwijaya_hackazon_images.pdf                              |     97.05 |
|    3 | openvas_heywoodlh_vulnerable_images.pdf                            |     94.26 |
|    4 | openvas_kirscht_metasploitable3-ub1404_images.pdf                  |     87.91 |
|    5 | openvas_citizenstig_nowasp_images.pdf                              |     64.92 |
|    6 | openvas_adamdoupe_wackopicko_images.pdf                            |     63.38 |
|    7 | openvas_raesene_bwapp_images.pdf                                   |     63.25 |
|    8 | openvas_hackersploit_bwapp-docker_images.pdf                       |     63.25 |
|    9 | openvas_acgpiano_sqli-labs_images.pdf                              |     44.32 |
|   10 | openvas_docker.bintray.io_jfrog_artifactory-oss_5.11.0_images.pdf  |     32.31 |

### Original PDFs (Text)

| Rank | File | Size (MB) |
|------|------|-----------|
|    1 | openvas_tleemcjr_metasploitable2.pdf                               |      1.75 |
|    2 | openvas_ianwijaya_hackazon.pdf                                     |      1.38 |
|    3 | openvas_heywoodlh_vulnerable.pdf                                   |      1.36 |
|    4 | openvas_kirscht_metasploitable3-ub1404.pdf                         |      1.29 |
|    5 | openvas_citizenstig_nowasp.pdf                                     |      0.96 |
|    6 | openvas_hackersploit_bwapp-docker.pdf                              |      0.95 |
|    7 | openvas_raesene_bwapp.pdf                                          |      0.95 |
|    8 | openvas_adamdoupe_wackopicko.pdf                                   |      0.95 |
|    9 | openvas_acgpiano_sqli-labs.pdf                                     |      0.69 |
|   10 | openvas_docker.bintray.io_jfrog_artifactory-oss_5.11.0.pdf         |      0.52 |

---

**Report Generated:** March 01, 2026  (clean dataset – 130 targets, removed 6 buggy from original 136)
**Source Directories:**  
- `vulnnet_scans_openvas/` (original formats: CSV, TXT, XML, PDF text)
- `benchmark/converted_datasets/` (converted formats: XLSX, DOCX, JSON, PDF images)

**Note:** This report separates the two PDF types to clearly show the size difference between text-based PDFs and image-based PDFs created for OCR testing. 6 buggy/duplicate scan targets removed: 4 duplicates (name contains ` (1)`) + 2 empty scans (`owasp_railsgoat`, `infosecwarrior_dns-lab_v2`).