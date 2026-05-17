#!/usr/bin/env python3
"""
ROI Scoring Engine — reads roi-data.json and computes 0-100 ROI scores
for every Carror OS component using configurable weights from harness.yaml.

Formula:
  Benefit = intercept_count × w_ic + time_saved × w_ts + quality_boost × w_qb + knowledge × w_kd
  Cost    = token_consumption × w_tc + maintenance × w_mb + false_positive × w_fpr + mental × w_mb2
  Raw ROI = Benefit / max(Cost, 1)
  Scaled  = min(100, raw_roi × scaling_factor)   # normalized to 0-100

Usage: python3 .claude/scripts/roi-score.py [--verbose] [--summary]
"""

import os, sys, json, re
from pathlib import Path

VERBOSE = "--verbose" in sys.argv
SUMMARY = "--summary" in sys.argv

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
STATE_DIR = PROJECT_DIR / ".omc" / "state"
ROI_DATA_FILE = STATE_DIR / "roi-data.json"
HARNESS_YAML = PROJECT_DIR / ".claude" / "harness.yaml"


def parse_yaml_simple(path):
    """Parse harness.yaml ROI weights without full YAML parser."""
    weights = {
        "benefit": {"intercept_count": 0.40, "time_saved": 0.25, "quality_boost": 0.20, "knowledge_deposit": 0.15},
        "cost": {"token_consumption": 0.30, "maintenance_burden": 0.30, "false_positive_rate": 0.25, "mental_burden": 0.15},
        "thresholds": {"low_roi": 10, "medium_roi": 30, "high_roi": 60},
    }
    try:
        with open(path) as f:
            content = f.read()
        # Parse roi block
        in_roi = False
        in_benefit = False
        in_cost = False
        in_thresholds = False
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("roi:"):
                in_roi = True
                continue
            if not in_roi:
                continue
            if stripped.startswith("weights:"):
                continue
            if stripped.startswith("benefit:"):
                in_benefit = True; in_cost = False; in_thresholds = False; continue
            if stripped.startswith("cost:"):
                in_cost = True; in_benefit = False; in_thresholds = False; continue
            if stripped.startswith("thresholds:"):
                in_thresholds = True; in_benefit = False; in_cost = False; continue
            if in_benefit:
                for key in weights["benefit"]:
                    if stripped.startswith(f"{key}:"):
                        try:
                            weights["benefit"][key] = float(stripped.split(":", 1)[1].strip())
                        except ValueError:
                            pass
            if in_cost:
                for key in weights["cost"]:
                    if stripped.startswith(f"{key}:"):
                        try:
                            weights["cost"][key] = float(stripped.split(":", 1)[1].strip())
                        except ValueError:
                            pass
            if in_thresholds:
                for key in weights["thresholds"]:
                    if stripped.startswith(f"{key}:"):
                        try:
                            weights["thresholds"][key] = float(stripped.split(":", 1)[1].strip())
                        except ValueError:
                            pass
            # Exit roi block
            if in_roi and not stripped.startswith(" ") and not stripped.startswith("\t") and stripped and not stripped.startswith("benefit") and not stripped.startswith("cost") and not stripped.startswith("thresholds") and not stripped.startswith("weights") and not stripped.startswith("roi"):
                if stripped != "" and ":" in stripped:
                    in_roi = False
    except Exception as e:
        if VERBOSE:
            print(f"[roi-score] Warning: could not parse harness.yaml: {e}, using defaults")
    return weights


def normalize_benefit(val, max_val):
    """Normalize benefit value to 0-100 scale against a max."""
    if max_val <= 0:
        return 0
    return min(100, (val / max_val) * 100)


def normalize_cost(val, max_val):
    """Normalize cost value to 0-100 scale (inverted — higher cost = worse)."""
    if max_val <= 0:
        return 0
    return min(100, (val / max_val) * 100)


def score_component(comp_data, weights, benefit_maxes, cost_maxes):
    """Calculate ROI score for a single component."""
    wb = weights["benefit"]
    wc = weights["cost"]

    # Compute raw benefit
    benefit = (
        normalize_benefit(comp_data.get("intercept_count", 0) or comp_data.get("usage_count", 0), benefit_maxes["intercept"]) * wb["intercept_count"] +
        normalize_benefit(comp_data.get("time_saved_minutes", 0), benefit_maxes["time_saved"]) * wb["time_saved"] +
        normalize_benefit(comp_data.get("quality_boost", 0) * 100, benefit_maxes["quality"]) * wb["quality_boost"] +
        normalize_benefit(comp_data.get("knowledge_deposit_refs", 0), benefit_maxes["knowledge"]) * wb["knowledge_deposit"]
    )

    # Compute raw cost
    # maintenance burden = lines * 0.7 + changes * 0.3
    maintenance = comp_data.get("maintenance_lines", 0) * 0.7 + comp_data.get("maintenance_changes_3m", 0) * 0.3
    cost = (
        normalize_cost(comp_data.get("token_consumption_per_call", 0) * comp_data.get("call_frequency_est", 0), cost_maxes["token"]) * wc["token_consumption"] +
        normalize_cost(maintenance, cost_maxes["maintenance"]) * wc["maintenance_burden"] +
        normalize_cost(comp_data.get("false_positive_rate", 0) * 100, cost_maxes["fpr"]) * wc["false_positive_rate"] +
        normalize_cost(comp_data.get("mental_burden", 0) * 10, cost_maxes["mental"]) * wc["mental_burden"]
    )

    # ROI = benefit - cost (simpler and more intuitive than ratio)
    # +50 centering: normalizes mid-range components around 50.
    # This produces a RANKING score (0-100), not an absolute ROI ratio.
    # Two components with the same score may have different benefit/cost profiles;
    # the score reflects relative position, not absolute return.
    # See .omc/state/roi-recommendations.md for methodology limitations.
    raw_roi = benefit - cost
    scaled = max(0, min(100, raw_roi + 50))  # ranking score, not absolute ROI

    return round(scaled, 1)


def compute_all_scores(roi_data, weights):
    """Score all components in all categories."""
    benefit_maxes = {"intercept": 1, "time_saved": 1, "quality": 1, "knowledge": 1}
    cost_maxes = {"token": 1, "maintenance": 1, "fpr": 1, "mental": 1}

    # First pass: find max values for normalization
    for category in ("hooks", "skills", "scripts"):
        for name, comp in roi_data["components"].get(category, {}).items():
            ic = comp.get("intercept_count", 0) or comp.get("usage_count", 0)
            benefit_maxes["intercept"] = max(benefit_maxes["intercept"], ic)
            ts = comp.get("time_saved_minutes", 0)
            benefit_maxes["time_saved"] = max(benefit_maxes["time_saved"], ts)
            qb = comp.get("quality_boost", 0) * 100
            benefit_maxes["quality"] = max(benefit_maxes["quality"], qb)
            kd = comp.get("knowledge_deposit_refs", 0)
            benefit_maxes["knowledge"] = max(benefit_maxes["knowledge"], kd)
            tc = comp.get("token_consumption_per_call", 0) * comp.get("call_frequency_est", 0)
            cost_maxes["token"] = max(cost_maxes["token"], tc)
            maintenance = comp.get("maintenance_lines", 0) * 0.7 + comp.get("maintenance_changes_3m", 0) * 0.3
            cost_maxes["maintenance"] = max(cost_maxes["maintenance"], maintenance)
            fpr = comp.get("false_positive_rate", 0) * 100
            cost_maxes["fpr"] = max(cost_maxes["fpr"], fpr)
            mb = comp.get("mental_burden", 0) * 10
            cost_maxes["mental"] = max(cost_maxes["mental"], mb)

    # Ensure no zero divisors
    for k in benefit_maxes:
        benefit_maxes[k] = max(benefit_maxes[k], 1)
    for k in cost_maxes:
        cost_maxes[k] = max(cost_maxes[k], 1)

    # Second pass: score
    results = []
    for category in ("hooks", "skills", "scripts"):
        for name, comp in roi_data["components"].get(category, {}).items():
            score = score_component(comp, weights, benefit_maxes, cost_maxes)
            results.append({
                "name": name,
                "category": category.rstrip("s"),  # "hook" / "skill" / "script"
                "roi_score": score,
                "intercept_count": comp.get("intercept_count", 0) or comp.get("usage_count", 0),
                "time_saved_minutes": comp.get("time_saved_minutes", 0),
                "quality_boost": comp.get("quality_boost", 0),
                "knowledge_deposit_refs": comp.get("knowledge_deposit_refs", 0),
                "maintenance_lines": comp.get("maintenance_lines", 0),
                "maintenance_changes_3m": comp.get("maintenance_changes_3m", 0),
                "false_positive_rate": comp.get("false_positive_rate", 0),
                "mental_burden": comp.get("mental_burden", 0),
            })

    results.sort(key=lambda r: r["roi_score"], reverse=True)
    return results, benefit_maxes, cost_maxes


def tier_label(score, thresholds):
    if score >= thresholds.get("high_roi", 60):
        return "high"
    elif score >= thresholds.get("medium_roi", 30):
        return "medium"
    else:
        return "low"


def main():
    if not ROI_DATA_FILE.exists():
        print(f"[roi-score] ERROR: {ROI_DATA_FILE} not found. Run roi-collector first.")
        return 1

    with open(ROI_DATA_FILE) as f:
        roi_data = json.load(f)

    weights = parse_yaml_simple(HARNESS_YAML)
    thresholds = weights["thresholds"]

    if VERBOSE:
        print(f"[roi-score] Weights: benefit={weights['benefit']}, cost={weights['cost']}")
        print(f"[roi-score] Thresholds: {thresholds}")

    results, bmax, cmax = compute_all_scores(roi_data, weights)

    if VERBOSE:
        print(f"[roi-score] Normalization: benefit_maxes={bmax}, cost_maxes={cmax}")

    # Summary output
    if SUMMARY:
        total = len(results)
        high = [r for r in results if tier_label(r["roi_score"], thresholds) == "high"]
        medium = [r for r in results if tier_label(r["roi_score"], thresholds) == "medium"]
        low = [r for r in results if tier_label(r["roi_score"], thresholds) == "low"]
        print(f"[roi-score] {total} components scored: {len(high)} high, {len(medium)} medium, {len(low)} low")
        print(f"\nTop 10 ROI:")
        for r in results[:10]:
            print(f"  {r['roi_score']:5.1f} [{r['category']}] {r['name']}")
        print(f"\nBottom 5 ROI:")
        for r in results[-5:]:
            print(f"  {r['roi_score']:5.1f} [{r['category']}] {r['name']}")

    # Write full results
    output = {
        "generated_at": roi_data.get("generated_at", ""),
        "weights": weights,
        "normalization_maxes": {"benefit": bmax, "cost": cmax},
        "results": results,
        "summary": {
            "total_components": len(results),
            "high_roi_count": len([r for r in results if tier_label(r["roi_score"], thresholds) == "high"]),
            "medium_roi_count": len([r for r in results if tier_label(r["roi_score"], thresholds) == "medium"]),
            "low_roi_count": len([r for r in results if tier_label(r["roi_score"], thresholds) == "low"]),
            "top_10": [{"name": r["name"], "category": r["category"], "roi_score": r["roi_score"]} for r in results[:10]],
            "bottom_5": [{"name": r["name"], "category": r["category"], "roi_score": r["roi_score"]} for r in results[-5:]],
        },
    }

    output_file = STATE_DIR / "roi-scores.json"
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"[roi-score] Complete: scores written to {output_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
