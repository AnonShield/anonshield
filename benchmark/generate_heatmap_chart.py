#!/usr/bin/env python3
"""
Generate 3-panel chart for Tabela 3:
  (A) Throughput (KB/s)  |  (B) Total Time (hours)  |  (C) Speedup vs v1.0
All versions (v1.0, v2.0, v3.0 strategies), CSV + JSON.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
SESSION = Path("benchmark/orchestrated_results/session_20260208_005447")
CSV_DATA   = SESSION / "00_cve_dataset_v3_10runs_csv"  / "benchmark_results.csv"
JSON_DATA  = SESSION / "01_cve_dataset_v3_10runs_json" / "benchmark_results.csv"
OVERHEAD   = SESSION / "02_overhead_calibration_10runs" / "benchmark_results.csv"
REGRESSION = SESSION / "03_regression_3runs"            / "benchmark_results.csv"

# ── v3.0 measured (10 runs) ──────────────────────────────────────────
def load_v3(path, fmt):
    df = pd.read_csv(path)
    df = df[df["status"] == "SUCCESS"]
    size_mb = df["file_size_mb"].iloc[0]
    size_kb = size_mb * 1024
    rows = []
    for strat, grp in df.groupby("strategy"):
        t = grp["wall_clock_time_sec"].mean()
        rows.append({
            "label": f"3.0_{strat}",
            "format": fmt,
            "time_sec": t,
            "time_hours": t / 3600,
            "tp_kbps": size_kb / t,
        })
    return rows, size_mb

csv_rows, csv_mb = load_v3(CSV_DATA, "CSV")
json_rows, json_mb = load_v3(JSON_DATA, "JSON")

# ── Overhead ─────────────────────────────────────────────────────────
oh = pd.read_csv(OVERHEAD)
oh = oh[oh["status"] == "SUCCESS"]
overhead = {v: g["wall_clock_time_sec"].mean() for v, g in oh.groupby("version")}

# ── v1.0/v2.0 estimated ─────────────────────────────────────────────
reg = pd.read_csv(REGRESSION)
reg = reg[reg["status"] == "SUCCESS"]

def estimate(version, strategy, extension, target_kb):
    mask = ((reg["version"] == version) &
            (reg["strategy"] == strategy) &
            (reg["file_extension"] == extension))
    sub = reg[mask].copy()
    if len(sub) < 3:
        return None
    oh_val = overhead.get(version, 0)
    avg = sub.groupby("file_size_kb")["wall_clock_time_sec"].mean().reset_index()
    avg["pt"] = avg["wall_clock_time_sec"] - oh_val
    avg = avg[avg["pt"] > 0]
    if len(avg) == 0:
        return None
    avg["tp"] = avg["file_size_kb"] / avg["pt"]
    return oh_val + (target_kb / avg["tp"].mean())

legacy_rows = []
for ver, strat in [(1.0, "default"), (2.0, "default")]:
    label = f"{ver:.0f}.0_{strat}"
    t = estimate(ver, strat, ".csv", csv_mb * 1024)
    if t:
        legacy_rows.append({"label": label, "format": "CSV",
                            "time_sec": t, "time_hours": t / 3600,
                            "tp_kbps": (csv_mb * 1024) / t})
    # v1.0 does not support JSON — only estimate JSON for v2.0
    if ver == 2.0:
        t = estimate(ver, strat, ".json", json_mb * 1024)
        if t:
            legacy_rows.append({"label": label, "format": "JSON",
                                "time_sec": t, "time_hours": t / 3600,
                                "tp_kbps": (json_mb * 1024) / t})

# ── Combine ──────────────────────────────────────────────────────────
df = pd.DataFrame(legacy_rows + csv_rows + json_rows)

order = ["1.0_default", "2.0_default",
         "3.0_standalone", "3.0_filtered", "3.0_hybrid", "3.0_presidio"]
display = ["v1.0 (est.)", "v2.0 (est.)",
           "3.0_standalone", "3.0_filtered", "3.0_hybrid", "3.0_presidio"]

def get_vals(col, fmt):
    vals = []
    for lb in order:
        rows = df[(df["label"] == lb) & (df["format"] == fmt)]
        vals.append(rows[col].values[0] if len(rows) else None)
    return vals

csv_tp    = get_vals("tp_kbps", "CSV")
json_tp   = get_vals("tp_kbps", "JSON")
csv_time  = get_vals("time_hours", "CSV")
json_time = get_vals("time_hours", "JSON")

# Speedup: CSV vs v1.0, JSON vs v2.0 (v1.0 has no JSON support)
v1_csv_tp  = csv_tp[0]
v2_json_tp = json_tp[1]  # v2.0 is the baseline for JSON
csv_speedup  = [tp / v1_csv_tp if tp else None for tp in csv_tp]
json_speedup = [tp / v2_json_tp if tp else None for tp in json_tp]

# ── Style ─────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.facecolor": "#FAFAFA",
    "figure.facecolor": "white",
})

c_csv  = "#2D7D9A"   # teal
c_json = "#E07B54"   # coral

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(13.5, 4.5))
fig.subplots_adjust(wspace=0.42, top=0.85, bottom=0.10)

y = np.arange(len(order))
bh = 0.34

# Shared legend at the top
fig.legend(
    handles=[
        plt.Rectangle((0, 0), 1, 1, fc=c_csv, ec="none", label=f"CSV ({csv_mb:.0f} MB)"),
        plt.Rectangle((0, 0), 1, 1, fc=c_json, ec="none", label=f"JSON ({json_mb:.0f} MB)"),
    ],
    loc="upper center", ncol=2, fontsize=9, frameon=False,
    bbox_to_anchor=(0.5, 0.97),
)

def style_ax(ax, title, xlabel):
    ax.set_title(title, fontsize=10, fontweight="bold", pad=10)
    ax.set_xlabel(xlabel, fontsize=8.5)
    ax.set_yticks(y)
    ax.set_yticklabels(display, fontsize=8.5)
    ax.set_xscale("log")
    ax.grid(axis="x", alpha=0.15, linestyle="-", color="#888888")
    ax.set_axisbelow(True)
    ax.axhline(1.5, color="#BBBBBB", linewidth=1.2, linestyle="-")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")
    ax.tick_params(colors="#555555", labelsize=8)
    ax.invert_yaxis()

def safe(vals):
    """Replace None with 0 for bar plotting."""
    return [v if v is not None else 0 for v in vals]

def add_labels(ax, y_pos, csv_vals, json_vals, fmt_fn, offset=1.2):
    for yi, (cv, jv) in enumerate(zip(csv_vals, json_vals)):
        if cv is not None and cv > 0:
            ax.text(cv * offset, yi - bh/2, fmt_fn(cv), va="center",
                    fontsize=7.5, color=c_csv, fontweight="bold")
        if jv is not None and jv > 0:
            ax.text(jv * offset, yi + bh/2, fmt_fn(jv), va="center",
                    fontsize=7.5, color=c_json, fontweight="bold")

# ── Panel A: Throughput ──────────────────────────────────────────────
ax1.barh(y - bh/2, safe(csv_tp),  bh, color=c_csv,  ec="none", zorder=3)
ax1.barh(y + bh/2, safe(json_tp), bh, color=c_json, ec="none", zorder=3)
style_ax(ax1, "(A) Throughput", "KB/s")
add_labels(ax1, y, csv_tp, json_tp,
           lambda v: f"{v:.1f}" if v < 10 else f"{v:.0f}")

# ── Panel B: Total Time ─────────────────────────────────────────────
ax2.barh(y - bh/2, safe(csv_time),  bh, color=c_csv,  ec="none", zorder=3)
ax2.barh(y + bh/2, safe(json_time), bh, color=c_json, ec="none", zorder=3)
style_ax(ax2, "(B) Total Time", "hours")
add_labels(ax2, y, csv_time, json_time,
           lambda v: f"{v:.1f} h" if v >= 1 else f"{v*60:.0f} min", offset=1.25)

# ── Panel C: Speedup ────────────────────────────────────────────────
ax3.barh(y - bh/2, safe(csv_speedup),  bh, color=c_csv,  ec="none", zorder=3)
ax3.barh(y + bh/2, safe(json_speedup), bh, color=c_json, ec="none", zorder=3)
style_ax(ax3, "(C) Speedup vs baseline", "fold-change")
ax3.axvline(1, color="#AAAAAA", linewidth=0.8, linestyle="--", zorder=2)
add_labels(ax3, y, csv_speedup, json_speedup,
           lambda v: f"{v:.0f}x" if v >= 10 else f"{v:.1f}x")


out_png = "benchmark/tabela3_heatmap.png"
out_pdf = "benchmark/tabela3_heatmap.pdf"
fig.savefig(out_png, dpi=300, bbox_inches="tight")
fig.savefig(out_pdf, bbox_inches="tight")
print(f"Saved: {out_png}")
print(f"Saved: {out_pdf}")
