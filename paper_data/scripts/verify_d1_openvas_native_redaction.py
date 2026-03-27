#!/usr/bin/env python3
"""
verify_d1_openvas_native_redaction.py
======================================
Reproduces the empirical claim from Section 3 of the paper:

  "11 of the 130 reports explicitly leaked 71 unique cryptographic hashes
   and TLS certificate fingerprints. Because these values are globally
   indexed by search engines, they trivialize exact asset re-identification,
   rendering the native anonymization fundamentally ineffective."

What the script does
--------------------
Step 1 — OpenVAS native (.anonymous) audit:
  Scans all 130 .anonymous files in D1 for <md5_fingerprint> and
  <sha256_fingerprint> tags. Identifies the 11 affected reports.

Step 2 — Unique value count:
  For each of the 11 affected reports, extracts unique sensitive values
  from the corresponding raw XML (TLS fingerprint tags + standalone
  colon-separated fingerprints + cryptographic hashes outside of public
  reference URLs). Sums per-file unique counts → 71.

Step 3 — AnonShield verification:
  Checks that every one of those 71 values (across all 11 files) is absent
  in the corresponding AnonShield-anonymized XML outputs for all four
  strategies: filtered, hybrid, standalone, presidio.

  The script automatically runs AnonShield on the 11 affected XML files and
  stores the outputs in:
      paper_data/scripts/verify_d1_output/
  Already-processed files are skipped on subsequent runs (cached).

  Note: TLS fingerprints and cryptographic hashes are detected by regex
  patterns in AnonShield — not by the NER model — so all four strategies
  produce identical redaction results for these values. The script
  nevertheless tests all four to confirm the paper's claim.

Usage (from workspace root):
    python3 paper_data/scripts/verify_d1_openvas_native_redaction.py

Expected output:
    Step 1: 11 / 130 .anonymous files expose TLS fingerprint tags     ✅
    Step 2: 71 unique sensitive values across those 11 reports         ✅
    Step 3: 0 / 71 values leaked in AnonShield output (all strategies) ✅

Actual output recorded during evaluation (2026-03-27):
----------------------------------------------------------------------
  D1 OpenVAS — Native Redaction Failure & AnonShield Verification
======================================================================

Step 1 — OpenVAS native .anonymous audit
  Total .anonymous files scanned : 130
  Files with TLS fingerprint tags: 11  ✅
    · openvas_dovecot_dovecot
    · openvas_glassfish_4.1
    · openvas_heywoodlh_vulnerable
    · openvas_ianwijaya_hackazon
    · openvas_ismisepaul_securityshepherd
    · openvas_jasonrivers_nagios
    · openvas_jboss_wildfly_10.1.0.Final
    · openvas_osixia_openldap_1.2.0
    · openvas_osixia_phpldapadmin_0.7.1
    · openvas_sameersbn_bind_9.11.3-20190706
    · openvas_tleemcjr_metasploitable2

Step 2 — Unique sensitive values per report (sum)
  openvas_dovecot_dovecot                                  4 values
  openvas_glassfish_4.1                                    3 values
  openvas_heywoodlh_vulnerable                            16 values
  openvas_ianwijaya_hackazon                               6 values
  openvas_ismisepaul_securityshepherd                      3 values
  openvas_jasonrivers_nagios                               4 values
  openvas_jboss_wildfly_10.1.0.Final                       3 values
  openvas_osixia_openldap_1.2.0                            4 values
  openvas_osixia_phpldapadmin_0.7.1                        6 values
  openvas_sameersbn_bind_9.11.3-20190706                   4 values
  openvas_tleemcjr_metasploitable2                        18 values
  ────────────────────────────────────────────────────────
  Sum of per-file unique values                           71  ✅

Step 3 — AnonShield redaction check (all 4 strategies)
  [filtered  ]  openvas_dovecot_dovecot                            ✅ all redacted
  [filtered  ]  openvas_glassfish_41                               ✅ all redacted
  [filtered  ]  openvas_heywoodlh_vulnerable                       ✅ all redacted
  [filtered  ]  openvas_ianwijaya_hackazon                         ✅ all redacted
  [filtered  ]  openvas_ismisepaul_securityshepherd                ✅ all redacted
  [filtered  ]  openvas_jasonrivers_nagios                         ✅ all redacted
  [filtered  ]  openvas_jboss_wildfly_101Final                     ✅ all redacted
  [filtered  ]  openvas_osixia_openldap_120                        ✅ all redacted
  [filtered  ]  openvas_osixia_phpldapadmin_071                    ✅ all redacted
  [filtered  ]  openvas_sameersbn_bind_9113-20190706               ✅ all redacted
  [filtered  ]  openvas_tleemcjr_metasploitable2                   ✅ all redacted
  [hybrid    ]  (same 11 files — all redacted)                     ✅ all redacted
  [standalone]  (same 11 files — all redacted)                     ✅ all redacted
  [presidio  ]  (same 11 files — all redacted)                     ✅ all redacted

  Total leaked values across all strategies : 0  ✅

======================================================================
  RESULT: paper claim reproduced ✅
  · 11/130 .anonymous reports expose TLS fingerprint tags
  · 71 unique sensitive values across those 11 reports
  · AnonShield redacts all 71 values in all strategies
======================================================================
"""
import glob
import os
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# Paths (relative to workspace root — adjust if running from elsewhere)
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(_HERE, "..", ".."))

D1_DIR   = os.path.join(WS, "paper_data", "datasets", "D1_openvas")
# Outputs generated on-the-fly by this script (gitignored, persists across runs)
ANON_OUT = os.path.join(_HERE, "verify_d1_output")

STRATEGIES = ["filtered", "hybrid", "standalone", "presidio"]

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------
# TLS fingerprint XML tags produced by OpenVAS
PAT_CERT_TAG = re.compile(
    r'<(md5_fingerprint|sha256_fingerprint|sha1_fingerprint)>'
    r'([^<]+)'
    r'</\1>'
)
# Colon-separated hex fingerprints/serials (≥ 10 bytes) outside of cert tags
PAT_COLON_HEX = re.compile(r'\b([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){9,})\b')
# Standalone MD5 / SHA-1 / SHA-256 hashes (not preceded/followed by alnum)
PAT_HASH = re.compile(
    r'(?<![/\w])([0-9a-fA-F]{32}|[0-9a-fA-F]{40}|[0-9a-fA-F]{64})(?![/\w])'
)
# Reference URL context — hashes inside these are public CVE references
URL_CTX = re.compile(
    r'(?:github\.com|gist\.github\.com|git\.php\.net|gitlab\.com)'
    r'/.*?(?:commit|blob)/'
)


def _read(path: str) -> str:
    return open(path, encoding="utf-8", errors="replace").read()


def has_tls_tags(content: str) -> bool:
    return bool(PAT_CERT_TAG.search(content))


def extract_unique_sensitive(content: str) -> set:
    """Return set of unique sensitive values in *content*."""
    found = set()
    for m in PAT_CERT_TAG.finditer(content):
        found.add(m.group(2).strip())
    for line in content.splitlines():
        for m in PAT_COLON_HEX.finditer(line):
            if not PAT_CERT_TAG.search(line):
                found.add(m.group(1))
        for m in PAT_HASH.finditer(line):
            seg = line[max(0, m.start() - 120): m.start()]
            if not URL_CTX.search(seg):
                found.add(m.group(1))
    return found


def sanitize_name(name: str) -> str:
    """Remove dots from folder name to match AnonShield output naming (hyphens kept).

    AnonShield's get_output_path() applies re.sub(r'[^\\w\\-]', '', stem),
    which removes dots but preserves hyphens and underscores.
    """
    return name.replace('.', '')


# ---------------------------------------------------------------------------
# Step 1 — Identify affected .anonymous files
# ---------------------------------------------------------------------------
def step1_find_tls_files(d1_dir: str):
    all_anon = sorted(glob.glob(
        os.path.join(d1_dir, "**", "*.anonymous"), recursive=True
    ))
    if not all_anon:
        print(f"ERROR: no .anonymous files found under {d1_dir}", file=sys.stderr)
        sys.exit(1)

    affected = []
    for fpath in all_anon:
        if has_tls_tags(_read(fpath)):
            affected.append(os.path.dirname(fpath))

    return len(all_anon), affected


# ---------------------------------------------------------------------------
# Step 2 — Count unique sensitive values in affected raw XMLs
# ---------------------------------------------------------------------------
def step2_count_values(affected_folders: list):
    per_file = {}
    for folder in affected_folders:
        name = os.path.basename(folder)
        xml = os.path.join(folder, f"{name}.xml")
        if not os.path.exists(xml):
            print(f"  WARNING: raw XML not found: {xml}", file=sys.stderr)
            per_file[name] = set()
            continue
        per_file[name] = extract_unique_sensitive(_read(xml))
    return per_file


# ---------------------------------------------------------------------------
# Step 3 — Verify AnonShield redacts every value
# ---------------------------------------------------------------------------

def generate_anonshield_outputs(affected_folders: list, per_file: dict,
                                 strategies: list, out_dir: str) -> None:
    """Run AnonShield on the 11 affected XML files for all strategies.

    Outputs are written to out_dir/<strategy>/anon_<name>.xml.
    Uses --no-report and --db-mode in-memory to speed up each run.
    Runtime: ~2–5 min on GPU, ~10–20 min on CPU (11 files × 4 strategies).
    """
    anon_py = os.path.join(WS, "anon.py")
    if not os.path.exists(anon_py):
        print(f"ERROR: anon.py not found at {anon_py}", file=sys.stderr)
        sys.exit(1)

    print(f"\n  Pre-computed AnonShield outputs not found.")
    print(f"  Generating outputs now — this may take several minutes.")
    print(f"  Output directory: {out_dir}")
    print()

    done = 0
    errors = 0

    for strat in strategies:
        strat_dir = os.path.join(out_dir, strat)
        os.makedirs(strat_dir, exist_ok=True)
        for folder in affected_folders:
            name = os.path.basename(folder)
            if not per_file.get(name):
                continue
            xml = os.path.join(folder, f"{name}.xml")
            if not os.path.exists(xml):
                continue
            san = sanitize_name(name)
            out_xml = os.path.join(strat_dir, f"anon_{san}.xml")
            if os.path.exists(out_xml):
                print(f"    [{strat:10s}] {name[:40]:<40s}  (cached)")
                continue
            print(f"    [{strat:10s}] {name[:40]:<40s}  ...", end="", flush=True)
            result = subprocess.run(
                [
                    "uv", "run", "anon.py", xml,
                    "--anonymization-strategy", strat,
                    "--output-dir", strat_dir,
                    "--no-report",
                    "--db-mode", "in-memory",
                    "--overwrite",
                ],
                cwd=WS,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"  ERROR (exit {result.returncode})")
                if result.stderr:
                    print(f"      {result.stderr.strip()[-200:]}", file=sys.stderr)
                errors += 1
            else:
                print("  done")
                done += 1

    print()
    if errors:
        print(f"  WARNING: {errors} file(s) failed to process.", file=sys.stderr)


def step3_verify_anonshield(per_file: dict, anon_out: str, strategies: list):
    results = {}   # (file, strategy) → set of leaked values
    missing = []

    for fname, raw_vals in per_file.items():
        if not raw_vals:
            continue
        san = sanitize_name(fname)
        for strat in strategies:
            anon_xml = os.path.join(anon_out, strat, f"anon_{san}.xml")
            if not os.path.exists(anon_xml):
                missing.append((fname, strat, anon_xml))
                continue
            anon_vals = extract_unique_sensitive(_read(anon_xml))
            leaked = raw_vals & anon_vals
            results[(fname, strat)] = leaked

    return results, missing


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print()
    print("=" * 70)
    print("  D1 OpenVAS — Native Redaction Failure & AnonShield Verification")
    print("=" * 70)

    # ── Step 1 ────────────────────────────────────────────────────────────
    total_anon, affected = step1_find_tls_files(D1_DIR)
    ok1 = len(affected) == 11
    print(f"\nStep 1 — OpenVAS native .anonymous audit")
    print(f"  Total .anonymous files scanned : {total_anon}")
    print(f"  Files with TLS fingerprint tags: {len(affected)}"
          f"  {'✅' if ok1 else '❌  (expected 11)'}")
    for folder in affected:
        print(f"    · {os.path.basename(folder)}")

    # ── Step 2 ────────────────────────────────────────────────────────────
    per_file = step2_count_values(affected)
    total_sum = sum(len(v) for v in per_file.values())
    ok2 = total_sum == 71
    print(f"\nStep 2 — Unique sensitive values per report (sum)")
    for fname, vals in per_file.items():
        print(f"  {fname:<50s}  {len(vals):3d} values")
    print(f"  {'─'*56}")
    print(f"  {'Sum of per-file unique values':<50s}  {total_sum:3d}"
          f"  {'✅' if ok2 else '❌  (expected 71)'}")

    # ── Step 3 — generate AnonShield outputs (cached across runs) ─────────
    generate_anonshield_outputs(affected, per_file, STRATEGIES, ANON_OUT)
    print(f"Step 3 — AnonShield redaction check (all 4 strategies)")
    print(f"  Outputs: {os.path.relpath(ANON_OUT, WS)}")

    # ── Step 3 — check for leaks ───────────────────────────────────────────
    results, missing = step3_verify_anonshield(per_file, ANON_OUT, STRATEGIES)
    all_leaked = [v for leaked in results.values() for v in leaked]
    ok3 = len(all_leaked) == 0 and not missing
    print()
    if missing:
        print(f"  ⚠️  {len(missing)} output file(s) not found (listed below)")
        for fname, strat, _ in missing[:5]:
            print(f"     {strat:12s} × {fname}")

    for (fname, strat), leaked in results.items():
        status = "✅ all redacted" if not leaked else f"⚠️  {len(leaked)} LEAKED"
        print(f"  [{strat:10s}]  {fname:<48s}  {status}")

    print(f"\n  Total leaked values across all strategies : {len(all_leaked)}"
          f"  {'✅' if ok3 else '❌'}")
    if all_leaked:
        for v in all_leaked[:5]:
            print(f"    leaked: {v}")

    # ── Final verdict ─────────────────────────────────────────────────────
    print()
    print("=" * 70)
    if ok1 and ok2 and ok3:
        print("  RESULT: paper claim reproduced ✅")
        print(f"  · {len(affected)}/130 .anonymous reports expose TLS fingerprint tags")
        print(f"  · {total_sum} unique sensitive values across those {len(affected)} reports")
        print(f"  · AnonShield redacts all {total_sum} values in all strategies")
    else:
        print("  RESULT: one or more checks did not match expected values ❌")
        if not ok1:
            print(f"    Step 1 expected 11, got {len(affected)}")
        if not ok2:
            print(f"    Step 2 expected 71, got {total_sum}")
        if not ok3:
            print(f"    Step 3 expected 0 leaks, got {len(all_leaked)}"
                  + (f" + {len(missing)} missing outputs" if missing else ""))
    print("=" * 70)
    print()

    sys.exit(0 if (ok1 and ok2 and ok3) else 1)


if __name__ == "__main__":
    main()
