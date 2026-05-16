"""
run_evaluation.py
==================
Evaluates the LLM Security Gateway against data/final_eval.csv.

Outputs:
  results/evaluation_results.csv   — per-prompt detailed results
  results/metrics_summary.json     — Accuracy, Precision, Recall, F1

Usage:
  python run_evaluation.py
"""

import os
import json
import time
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report
)

# ── Make sure results dir exists ──────────────────────────────────────────────
os.makedirs("results", exist_ok=True)

# ── FastAPI test client ───────────────────────────────────────────────────────
# httpx >= 0.20 changed TestClient; wrap in try/except for compatibility
try:
    from starlette.testclient import TestClient
except ImportError:
    from fastapi.testclient import TestClient

from app.main import app
client = TestClient(app, raise_server_exceptions=False)

# ── Load dataset ──────────────────────────────────────────────────────────────
CSV_PATH = "data/final_eval.csv"
if not os.path.isfile(CSV_PATH):
    raise FileNotFoundError(
        f"{CSV_PATH} not found. Run: python generate_dataset.py"
    )

df = pd.read_csv(CSV_PATH)
print(f"[INFO] Loaded {len(df)} prompts from {CSV_PATH}")
print(f"[INFO] Expected policy distribution:\n{df['expected_policy'].value_counts().to_string()}\n")

# ── Evaluation loop ───────────────────────────────────────────────────────────
results = []

for _, row in df.iterrows():
    prompt_id      = row["id"]
    prompt         = row["prompt"]
    expected       = row["expected_policy"]   # Allow | Mask | Block

    try:
        t0 = time.perf_counter()
        resp = client.post("/analyze", json={"prompt": prompt})
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        if resp.status_code == 200:
            data           = resp.json()
            actual         = data.get("decision", "Error")
            final_risk     = data.get("final_risk", -1)
            rule_score     = data.get("rule_score", -1)
            semantic_score = data.get("semantic_score", -1)
            pii_entities   = str(data.get("pii_entities", []))
            reason_codes   = str(data.get("reason_codes", []))
        else:
            actual         = "Error"
            final_risk     = -1
            rule_score     = -1
            semantic_score = -1
            pii_entities   = "[]"
            reason_codes   = f"HTTP {resp.status_code}"

    except Exception as exc:
        actual         = "Error"
        final_risk     = -1
        rule_score     = -1
        semantic_score = -1
        pii_entities   = "[]"
        reason_codes   = str(exc)[:100]
        latency_ms     = -1

    match = (actual == expected)

    results.append({
        "id":              prompt_id,
        "prompt":          prompt[:80] + ("..." if len(prompt) > 80 else ""),
        "language":        row.get("language", "en"),
        "attack_type":     row.get("attack_type", "none"),
        "has_pii":         row.get("has_pii", False),
        "expected_policy": expected,
        "actual_decision": actual,
        "match":           match,
        "final_risk":      final_risk,
        "rule_score":      rule_score,
        "semantic_score":  semantic_score,
        "pii_entities":    pii_entities,
        "reason_codes":    reason_codes,
        "latency_ms":      latency_ms,
    })

    status_icon = "PASS" if match else "FAIL"
    print(f"  [{status_icon}] id={prompt_id:3d} | expected={expected:5s} "
          f"got={actual:5s} | risk={final_risk:.2f} | {prompt[:50]!r}")

# ── Save detailed results CSV ─────────────────────────────────────────────────
results_df = pd.DataFrame(results)
results_df.to_csv("results/evaluation_results.csv", index=False)
print(f"\n[INFO] Detailed results saved to results/evaluation_results.csv")

# ── Filter out Error rows for metric calculation ──────────────────────────────
valid_df = results_df[results_df["actual_decision"] != "Error"].copy()
error_count = len(results_df) - len(valid_df)
if error_count > 0:
    print(f"[WARN] {error_count} prompts returned errors and are excluded from metrics.")

y_true = valid_df["expected_policy"].tolist()
y_pred = valid_df["actual_decision"].tolist()

# ── Overall accuracy ──────────────────────────────────────────────────────────
overall_accuracy = round(accuracy_score(y_true, y_pred), 4)

# ── Per-class metrics (Block, Mask, Allow) ────────────────────────────────────
labels = ["Block", "Mask", "Allow"]
precision_per = precision_score(y_true, y_pred, labels=labels,
                                average=None, zero_division=0)
recall_per    = recall_score(   y_true, y_pred, labels=labels,
                                average=None, zero_division=0)
f1_per        = f1_score(       y_true, y_pred, labels=labels,
                                average=None, zero_division=0)

# ── Macro / weighted averages ─────────────────────────────────────────────────
precision_macro  = round(precision_score(y_true, y_pred, average="macro",    zero_division=0), 4)
recall_macro     = round(recall_score(   y_true, y_pred, average="macro",    zero_division=0), 4)
f1_macro         = round(f1_score(       y_true, y_pred, average="macro",    zero_division=0), 4)
precision_wt     = round(precision_score(y_true, y_pred, average="weighted", zero_division=0), 4)
recall_wt        = round(recall_score(   y_true, y_pred, average="weighted", zero_division=0), 4)
f1_wt            = round(f1_score(       y_true, y_pred, average="weighted", zero_division=0), 4)

# ── Build metrics dict ────────────────────────────────────────────────────────
per_class = {}
for i, label in enumerate(labels):
    per_class[label] = {
        "precision": round(float(precision_per[i]), 4),
        "recall":    round(float(recall_per[i]),    4),
        "f1_score":  round(float(f1_per[i]),        4),
        "support":   int(y_true.count(label)),
    }

# ── Confusion counts ──────────────────────────────────────────────────────────
total         = len(valid_df)
correct       = int(valid_df["match"].sum())
wrong         = total - correct

attack_rows   = valid_df[valid_df["expected_policy"] == "Block"]
pii_rows_     = valid_df[valid_df["expected_policy"] == "Mask"]
benign_rows   = valid_df[valid_df["expected_policy"] == "Allow"]

attack_acc  = round(float(accuracy_score(attack_rows["expected_policy"],
                                          attack_rows["actual_decision"])), 4) if len(attack_rows) else 0
pii_acc     = round(float(accuracy_score(pii_rows_["expected_policy"],
                                          pii_rows_["actual_decision"])),    4) if len(pii_rows_) else 0
benign_acc  = round(float(accuracy_score(benign_rows["expected_policy"],
                                          benign_rows["actual_decision"])),  4) if len(benign_rows) else 0

avg_latency = round(float(valid_df[valid_df["latency_ms"] >= 0]["latency_ms"].mean()), 2)
max_latency = round(float(valid_df[valid_df["latency_ms"] >= 0]["latency_ms"].max()),  2)

metrics = {
    "evaluation_summary": {
        "total_prompts":   len(df),
        "evaluated":       total,
        "errors_skipped":  error_count,
        "correct":         correct,
        "wrong":           wrong,
        "overall_accuracy": overall_accuracy,
    },
    "per_category_accuracy": {
        "attack_block_accuracy":  attack_acc,
        "pii_mask_accuracy":      pii_acc,
        "benign_allow_accuracy":  benign_acc,
    },
    "macro_averages": {
        "precision": precision_macro,
        "recall":    recall_macro,
        "f1_score":  f1_macro,
    },
    "weighted_averages": {
        "precision": precision_wt,
        "recall":    recall_wt,
        "f1_score":  f1_wt,
    },
    "per_class_metrics": per_class,
    "latency_ms": {
        "average": avg_latency,
        "max":     max_latency,
    },
    "classification_report": classification_report(
        y_true, y_pred, labels=labels, zero_division=0
    ),
}

with open("results/metrics_summary.json", "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=2, ensure_ascii=False)

# ── Print summary ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  EVALUATION SUMMARY")
print("=" * 60)
print(f"  Total Prompts       : {len(df)}")
print(f"  Evaluated           : {total}")
print(f"  Correct Decisions   : {correct}  ({overall_accuracy * 100:.1f}%)")
print(f"  Wrong  Decisions    : {wrong}")
print(f"  Error / Skipped     : {error_count}")
print()
print(f"  Attack Block Acc    : {attack_acc  * 100:.1f}%")
print(f"  PII Mask Acc        : {pii_acc     * 100:.1f}%")
print(f"  Benign Allow Acc    : {benign_acc  * 100:.1f}%")
print()
print(f"  Macro  Precision    : {precision_macro}")
print(f"  Macro  Recall       : {recall_macro}")
print(f"  Macro  F1-Score     : {f1_macro}")
print(f"  Weighted F1-Score   : {f1_wt}")
print()
print(f"  Avg Latency         : {avg_latency} ms")
print(f"  Max Latency         : {max_latency} ms")
print("=" * 60)
print("\n[INFO] Metrics saved to results/metrics_summary.json")
print("[INFO] Detailed CSV  -> results/evaluation_results.csv")
