# Research Artefacts

> **Claims verification, considered seals (Available/SeloD, Functional/SeloF, Sustainable/SeloS, Reproducible/SeloR), minimal test, and full reproduction instructions are documented in the [README](../README.md).**

Dataset D2 is subject to a data-sharing agreement with CAIS/RNP and cannot be publicly redistributed. All other artefacts are publicly available at the links below.

## Tool

- Source code and documentation: https://github.com/AnonShield/tool
- Docker image (CPU and GPU variants): https://hub.docker.com/r/anonshield/anon

## Datasets

- **D1** — OpenVAS (public, tracked in git): https://github.com/AnonShield/tool/tree/main/paper_data/datasets/D1_openvas
- **D3** — Mock CAIS (public, compressed): https://github.com/AnonShield/tool/tree/main/paper_data/datasets/D3_mock_cais
- **D2** — CAIS/RNP: private; contact data owner for access.

## Benchmark results

- Per-experiment CSVs and consolidated results: https://github.com/AnonShield/tool/tree/main/paper_data/results_paper

## Accuracy evaluation

- Annotated outputs (one XLSX per strategy/version), sampling protocol, and ground-truth CSV: https://github.com/AnonShield/tool/tree/main/paper_data/evaluation
- Annotation manual (criteria, edge cases, and decision flow): https://github.com/AnonShield/tool/blob/main/paper_data/evaluation/ANNOTATION_MANUAL.md

## Configuration files and reproduction scripts

- Anonymisation configs (one JSON per dataset): https://github.com/AnonShield/tool/tree/main/paper_data/configs
- Full benchmark reproduction and claim spot-check scripts: https://github.com/AnonShield/tool/tree/main/paper_data/scripts
