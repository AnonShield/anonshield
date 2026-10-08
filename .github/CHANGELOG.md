# Changelog

All notable changes to AnonShield will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note:** AnonShield is the third generation of this tool, succeeding AnonLFI v1.0 and v2.0. Version numbers in this changelog correspond to AnonShield releases only.

---

## [Unreleased]

### Added

- GPU image in two PyTorch builds: `anonshield/anon:gpu` (CUDA 13.0: NVIDIA driver 580+, RTX 20xx or newer, required for RTX 50xx) and `anonshield/anon:gpu-cu126` (older GPUs and drivers). `docker/run.sh --gpu` and `run.ps1 --gpu` pick one from `nvidia-smi`; `ANON_GPU_IMAGE` overrides.
- Startup check of the GPU against the installed PyTorch build: an unsupported GPU or a driver too old for the build is reported, and the run falls back to the CPU instead of failing with "no kernel image is available".
- `pt` dependency group with the Portuguese spaCy pipeline (`uv sync --group pt`); both images ship it.
- CI runs on every pull request, before the merge: end-to-end CLI tests over every text format and strategy, the web backend tests (with Redis), and the CLI Docker images (built and smoke-tested). On `main`, images are pushed and the app deployed only after all of them pass.

### Changed

- Default `--ner-aggregation-strategy` is `simple`. With `max`, multi-word entities came back cut ("New York" became `[LOCATION_...] York`).
- `--entities` is a positive filter in every strategy: no other type is anonymized, including raw NER labels such as `DATE`. Word-list and custom-pattern labels are valid values, and the supported list follows `--lang` (`BR_CPF`, `BR_CNPJ`, ...).
- Preserved types are still detected and keep their span: a preserved IP address is no longer anonymized as `PHONE_NUMBER`.
- `--allow-list` keeps everything inside an allowed term (an allowed e-mail no longer loses its parts to the `HOSTNAME` pattern).
- `--ner-score-threshold` applies to NER results only, not to the regex recognizers.
- XML field paths are root-first dot paths (`tickets.ticket.notes`, attributes as `tickets.ticket.@reporter`); XPath-style slashes are accepted in rules.
- `standalone` and `regex` fail instead of writing a text unchanged when its detection raises.
- The NER model is cached in `HF_HOME=/app/models/huggingface`, on the `/app/models` volume; after the first download, runs make no network call.
- Frontend on SvelteKit 3 (kit 3.0.1, adapter-node 6): the configuration moved from `svelte.config.js` to `vite.config.ts`, `$lib` imports became `#lib` (package.json `imports`), `PUBLIC_API_URL` is declared in `src/env.ts` and read from `$app/env/public`. Pages, navigation and the upload flow behave as before. The unused `adapter-auto` and the `cookie` override (for Kit 2's cookie 0.6) were removed.
- CI builds the frontend on Node 22, the major of the production image (SvelteKit 3 needs 22.17 or newer); Dependabot skips the redis major until it can be adopted.
- Docker wrappers (`run.sh`, `run.ps1`) need no setup: without `ANON_SECRET_KEY` they create a random key in `./anon/secret.key` on the first run and reuse it, so `./run.sh file.csv` works right after downloading the script. The key reaches the container by name instead of on the `docker run` command line (readable by any local user with `ps`).
- On Linux, `run.sh` runs the container as the calling user. The output, the mapping database and the model cache used to be owned by root, so they could not be edited or removed without sudo; an `./anon` folder left that way by an older version is handed back on the next run.
- Output file names keep spaces and inner dots (`nota final.txt` gives `anon_nota final.txt`, not `anon_notafinal.txt`).
- README: Docker quick start; the Docker guide drops the key-generation step.
- Web app on your own machine: `cd web && make local` builds and starts the stack behind an internal proxy on http://localhost:8080. The documented command published the frontend and the API on two ports, but the frontend calls `/api` on its own origin, so the app could not reach the API (and the `PUBLIC_API_URL` it set never reached the build).
- Dependencies: transformers 5.18, cryptography 50, urllib3 2.8, torch 2.14.1 and frontend updates (devalue 5.9.4). `pyproject.toml` overrides the `transformers<5` pin of spacy-huggingface-pipelines and the `cryptography<49` pin of presidio-anonymizer.

### Fixed

- `--preserve-row-context` left CSV files unchanged (pandas 3 copy-on-write) and wrote txt/docx/pdf batches in clear text when their first line was a stoplist word, a short line or a number.
- `standalone` saw only the first ~512 tokens of each text and glued pseudonyms to the previous word.
- `--word-list` and `--custom-patterns` worked only with the `regex` strategy.
- `fields_to_exclude` did not protect a value that also appeared in an anonymized CSV column, XLSX column or XML path.
- A `fields_to_anonymize` config left txt, pdf, docx and image files of the same run in clear text.
- `--slug-length 0` without a secret key wrote the original text in `standalone`, `regex` and `hybrid`.
- `--regex-priority` crashed (score above 1.0); `--generate-ner-data` crashed with `standalone`/`regex`; `--lang` other than `en`/`pt` crashed the Presidio strategies; `--lang pt` failed in a uv virtualenv.
- XML comments crashed the processor; `force_anonymize` ignored numeric JSON values and XLSX cells; invalid JSON produced `{}` instead of an error.
- Web: the secret key typed for a job was ignored (jobs were hashed with the server key).
- Phone numbers in international (`+1 212 555 0198`, `+44 20 7946 0958`) and North American (`(212) 555-0198`, `212-555-0198`) form were not detected by the regex recognizers, so the `regex` strategy left them in clear text; `(51) 99999-9999` lost its `(` outside the pseudonym; with `--lang pt` a 16-digit card number was labelled `BR_TITULO_ELEITORAL`.
- Docker wrappers: `--slug-length 0` was refused without a key, although the docs say it needs none; `run.ps1` reported "Output is in ..." after a failed run; Docker not installed, not running or not accessible to the user now get distinct messages.
- CI: on `main`, a merge that did not touch the CLI image failed the "CLI images" job (its push step ran with nothing built).
- Run output noise: Presidio's "Recognizer not added to registry" lines (one per recognizer of another language on every run; the code silenced a logger name Presidio does not use), the transformers warning that the tokenizer has "an incorrect regex pattern" (a false positive for models whose config has no `transformers_version`; tokenization is not changed) and the Hub's "unauthenticated requests" notice when downloading the model.
- Deploy: the runner was on the old server, so deploys since the move to the new host updated a copy nobody served while the health check (site up) still passed. The web images are now built in CI and pushed to GHCR, the host pulls them, and the deploy fails unless the public site reports the deployed commit.
- Web backend image: a recursive `chown` duplicated the virtualenv into a second layer; the image goes from 5 GB to 2.6 GB.
- Image workflow: exporting the GPU build cache ran the job past its 60-minute timeout (the images were already pushed); GPU builds now reuse the CPU build cache and export none.
- Deploy: the job pulled base images with an expired Docker Hub login stored on the host; it now logs in with the repository secret.
- Docker: `anonshield/anon:gpu` shipped CPU-only PyTorch; the NER model was downloaded again on every run; `run.sh`/`run.ps1` dropped the input path after a boolean flag and did not mount `--custom-patterns`/`--config` files.

### Removed

- The `hybrid` strategy: it ran the same Presidio detection as `filtered` with its own replacement loop and gave the same results (SBRC 2026 paper, Table 8: 733 TP, 63 FP, 27 FN, F1 94.2% for both; throughput within 3%). `--anonymization-strategy hybrid`, profiles with `strategy: hybrid` and the web API still accept the name and run `filtered`, with a warning; the interface no longer offers it.
- SLM/Ollama integration: the `slm` strategy, the `--slm-*` and `--ollama-*` flags, `src/anon/slm/`, `scripts/slm_regex_generator.py`, and the Ollama services in `docker/docker-compose.yml`.
- `curl` from the runtime image (only the Ollama integration used it).

### Security

- Fixes 18 Dependabot advisories in transformers, cryptography, urllib3 and devalue.

---

<!-- Add new releases above this line -->

<!-- Links -->
[Unreleased]: https://github.com/AnonShield/anonshield/commits/main
