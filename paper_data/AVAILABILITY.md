# Research Artefacts

> **Claims verification, considered seals (Available/SeloD, Functional/SeloF, Sustainable/SeloS, Reproducible/SeloR), and minimal test are documented in the [README](../README.md).**

> **Full experiment reproduction instructions, dataset descriptions, and benchmark schema are documented in [EXPERIMENTS.md](EXPERIMENTS.md).**

Dataset D2 is subject to a data-sharing agreement with CAIS/RNP and cannot be publicly redistributed. All other artefacts are publicly available at the links below.

## Tool

- [Source code and documentation](../README.md)
- Docker image (CPU and GPU variants): https://hub.docker.com/r/anonshield/anon

## Datasets

- **D1** — OpenVAS (public, tracked in git): [paper_data/datasets/D1_openvas](datasets/D1_openvas)
- **D3** — Mock CAIS (public, compressed): [paper_data/datasets/D3_mock_cais](datasets/D3_mock_cais)
- **D2** — CAIS/RNP: private; contact data owner for access.

## Benchmark results

- Per-experiment CSVs and consolidated results: [paper_data/results_paper](results_paper)

## Accuracy evaluation

- Annotated outputs (one XLSX per strategy/version) and sampling protocol: [paper_data/evaluation](evaluation)
- Annotation manual (criteria, edge cases, and decision flow): [ANNOTATION_MANUAL.md](evaluation/ANNOTATION_MANUAL.md)

## Configuration files and reproduction scripts

- Anonymisation configs (one JSON per dataset): [paper_data/configs](configs)
- Full benchmark reproduction and claim spot-check scripts: [paper_data/scripts](scripts)
