#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np


def analyze_evolution(json_path: str):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    problems = []
    level_data: Dict[int, Dict[str, list]] = {}

    for problem in data:
        if "creativity_evaluation" not in problem:
            continue

        eval_data = problem["creativity_evaluation"]
        avg_score = eval_data.get("average_overall_score", 0)
        problems.append({
            "id": problem["problem_id"],
            "avg_score": avg_score,
            "level_scores": eval_data.get("level_scores", {}),
        })

        for level_str, scores in eval_data.get("level_scores", {}).items():
            level = int(level_str)
            # Ensure level container is initialized
            if level not in level_data:
                level_data[level] = {"similarities": [], "creativities": [], "pass_rates": []}
            if scores.get("similarity") is not None:
                level_data[level]["similarities"].append(scores["similarity"])
                level_data[level]["creativities"].append(scores["creativity"])
            level_data[level]["pass_rates"].append(scores["pass@1"])

    print("=" * 70)
    print("📊 CREATIVITY ANALYSIS SUMMARY (Evolution)")
    print("=" * 70)

    print(f"\n📋 By Problem (Total: {len(problems)} problems):")
    print(f"  {'Problem':<15} {'Avg Overall Score':<20} {'Normalized':<15}")
    print(f"  {'-'*50}")
    for p in sorted(problems, key=lambda x: x["avg_score"], reverse=True):
        normalized = p["avg_score"] / 100.0
        print(f"  {p['id']:<15} {p['avg_score']:<20.2f} {normalized:<15.4f}")

    if problems:
        overall_avg = sum(p["avg_score"] for p in problems) / len(problems)
        overall_normalized = overall_avg / 100.0
        print(f"\n  {'OVERALL':<15} {overall_avg:<20.2f} {overall_normalized:<15.4f}")

    print(f"\n📈 By Level:")
    print(f"  {'Level':<8} {'Pass Rate':<12} {'Avg Sim':<12} {'Avg Creat':<12} {'Normalized':<12}")
    print(f"  {'-'*60}")
    for level in sorted(level_data.keys()):
        ld = level_data[level]
        if not ld["pass_rates"]:
            continue
        pass_rate = sum(ld["pass_rates"]) / len(ld["pass_rates"])
        avg_sim = sum(ld["similarities"]) / len(ld["similarities"]) if ld["similarities"] else 0
        avg_creat = sum(ld["creativities"]) / len(ld["creativities"]) if ld["creativities"] else 0
        normalized = avg_creat / 100.0
        print(f"  Level {level:<2} {pass_rate:<12.2%} {avg_sim:<12.4f} {avg_creat:<12.2f} {normalized:<12.4f}")

    return problems, level_data


def plot_evolution(problems, level_data, save_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Creativity Analysis (Evolution)", fontsize=16, fontweight="bold")

    ax1 = axes[0, 0]
    scores = [p["avg_score"] for p in problems]
    problem_ids = [p["id"].replace("problem_", "P") for p in problems]
    colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(scores)))
    ax1.bar(problem_ids, scores, color=colors, alpha=0.8)
    if scores:
        ax1.axhline(y=np.mean(scores), color="red", linestyle="--", linewidth=2, label=f"Mean: {np.mean(scores):.1f}")
    ax1.set_ylabel("Avg Overall Score", fontsize=11, fontweight="bold")
    ax1.set_title("Score by Problem", fontsize=12, fontweight="bold")
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3)

    ax2 = axes[0, 1]
    levels = sorted(level_data.keys())
    creativities = [sum(level_data[l]["creativities"]) / len(level_data[l]["creativities"]) if level_data[l]["creativities"] else 0 for l in levels]
    ax2.plot(levels, creativities, marker="o", linewidth=2.5, markersize=8, color="#2ecc71")
    ax2.fill_between(levels, creativities, alpha=0.3, color="#2ecc71")
    ax2.set_xlabel("Constraint Level", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Avg Creativity", fontsize=11, fontweight="bold")
    ax2.set_title("Creativity vs Constraint Level", fontsize=12, fontweight="bold")
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(levels)

    ax3 = axes[1, 0]
    all_sims = []
    all_creats = []
    for level in levels:
        all_sims.extend(level_data[level]["similarities"])
        all_creats.extend(level_data[level]["creativities"])
    ax3.scatter(all_sims, all_creats, alpha=0.6, s=60, c=range(len(all_sims)), cmap="coolwarm")
    ax3.plot([0, 1], [100, 0], "k--", alpha=0.3, linewidth=1, label="y=100(1-x)")
    ax3.set_xlabel("Similarity", fontsize=11, fontweight="bold")
    ax3.set_ylabel("Creativity", fontsize=11, fontweight="bold")
    ax3.set_title("Similarity vs Creativity", fontsize=12, fontweight="bold")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    ax4 = axes[1, 1]
    pass_rates = [sum(level_data[l]["pass_rates"]) / len(level_data[l]["pass_rates"]) if level_data[l]["pass_rates"] else 0 for l in levels]
    bars = ax4.bar(levels, pass_rates, color=["#3498db" if r >= 0.8 else "#e74c3c" for r in pass_rates], alpha=0.8)
    ax4.axhline(y=0.8, color="orange", linestyle="--", linewidth=2, label="80% threshold")
    ax4.set_xlabel("Constraint Level", fontsize=11, fontweight="bold")
    ax4.set_ylabel("Pass Rate", fontsize=11, fontweight="bold")
    ax4.set_title("Success Rate by Level", fontsize=12, fontweight="bold")
    ax4.set_ylim([0, 1.1])
    ax4.set_xticks(levels)
    ax4.legend()
    ax4.grid(axis="y", alpha=0.3)

    for bar, rate in zip(bars, pass_rates):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width() / 2.0, height + 0.02, f"{rate:.1%}", ha="center", va="bottom", fontweight="bold", fontsize=9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"\n📊 Plot saved to: {save_path}")


# ================= Infer branch (new logic) ================= #
def load_infer_run(input_path: str) -> Tuple[Path, List[Dict], Dict]:
    p = Path(input_path)
    if p.is_dir():
        run_dir = p
        results_path = run_dir / "results.json"
        summary_path = run_dir / "summary.json"
    else:
        results_path = p
        run_dir = results_path.parent
        summary_path = run_dir / "summary.json"
    if not results_path.exists():
        raise FileNotFoundError(f"results.json not found: {results_path}")
    if not summary_path.exists():
        # Attempt to load partial, or compute on the fly
        partial = run_dir / "summary.partial.json"
        if partial.exists():
            with partial.open("r", encoding="utf-8") as s:
                summary = json.load(s)
            with results_path.open("r", encoding="utf-8") as r:
                results = json.load(r)
            return run_dir, results, summary
        # Compute from results.json if present
        with results_path.open("r", encoding="utf-8") as r:
            results = json.load(r)
        # Build summary structure compatible with infer
        summary_dict: Dict[int, Dict[str, float]] = {}
        for it in results:
            L = int(it.get("level", 0))
            if L == 0:
                continue
            s = summary_dict.setdefault(L, {"total": 0, "success": 0, "sum_novelty": 0.0, "sum_creativity": 0.0})
            s["total"] += 1
            s["success"] += 1 if it.get("success") else 0
            s["sum_novelty"] += float(it.get("novelty", 0.0))
            s["sum_creativity"] += float(it.get("creativity", 0.0))
        for L, s in list(summary_dict.items()):
            if s["total"]:
                s["pass_rate"] = round(s["success"] / s["total"], 4)
                s["avg_novelty"] = round(s["sum_novelty"] / s["total"], 4)
                s["avg_creativity"] = round(s["sum_creativity"] / s["total"], 4)
                del s["sum_novelty"]
                del s["sum_creativity"]
        summary = {"by_level": summary_dict, "note": "computed ad-hoc; level 0 excluded"}
        return run_dir, results, summary
    with results_path.open("r", encoding="utf-8") as r:
        results = json.load(r)
    with summary_path.open("r", encoding="utf-8") as s:
        summary = json.load(s)
    return run_dir, results, summary


def analyze_infer(results: List[Dict], summary: Dict):
    by_level = summary.get("by_level", {})
    levels = sorted(int(k) for k in by_level.keys())
    pass_rates = [by_level[str(l)].get("pass_rate", 0.0) for l in levels]
    avg_novelty = [by_level[str(l)].get("avg_novelty", 0.0) for l in levels]
    avg_creativity = [by_level[str(l)].get("avg_creativity", 0.0) for l in levels]

    sims_base: List[float] = []
    creats: List[float] = []
    for r in results:
        lvl = int(r.get("level", 0))
        if lvl == 0:
            continue
        sims_base.append(float(r.get("sim_to_baseline", 0.0)))
        creats.append(float(r.get("creativity", 0.0)))

    success_counts = [by_level[str(l)].get("success", 0) for l in levels]
    total_counts = [by_level[str(l)].get("total", 0) for l in levels]
    return levels, pass_rates, avg_novelty, avg_creativity, sims_base, creats, success_counts, total_counts


def plot_infer(levels, pass_rates, avg_novelty, avg_creativity, sims_base, creats, success_counts, total_counts, save_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Creativity Analysis (Infer)", fontsize=16, fontweight="bold")

    ax1 = axes[0, 0]
    bars1 = ax1.bar(levels, pass_rates, color=["#2e86de" if r >= 0.8 else "#e67e22" if r >= 0.5 else "#e74c3c" for r in pass_rates])
    ax1.set_title("Pass Rate by Level", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Constraint Level")
    ax1.set_ylabel("Pass Rate")
    ax1.set_ylim(0, 1.05)
    ax1.grid(axis="y", alpha=0.3)
    for b, r in zip(bars1, pass_rates):
        ax1.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02, f"{r:.0%}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax2 = axes[0, 1]
    ax2.plot(levels, avg_novelty, marker="o", linewidth=2, label="Avg Novelty", color="#8e44ad")
    ax2.plot(levels, avg_creativity, marker="s", linewidth=2, label="Avg Creativity", color="#27ae60")
    ax2.fill_between(levels, avg_creativity, alpha=0.2, color="#27ae60")
    ax2.set_title("Novelty & Creativity vs Level", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Constraint Level")
    ax2.set_ylabel("Score (0..1)")
    ax2.set_xticks(levels)
    ax2.set_ylim(0, 1.05)
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    ax3 = axes[1, 0]
    ax3.scatter(sims_base, creats, s=60, alpha=0.6, c=range(len(sims_base)), cmap="coolwarm")
    ax3.plot([0, 1], [1, 0], "k--", alpha=0.3, linewidth=1, label="y = 1 - x")
    ax3.set_title("Similarity-to-Baseline vs Creativity", fontsize=12, fontweight="bold")
    ax3.set_xlabel("Similarity to Baseline (0..1)")
    ax3.set_ylabel("Creativity (0..1)")
    ax3.grid(True, alpha=0.3)
    ax3.legend()

    ax4 = axes[1, 1]
    width = 0.35
    lvls = list(range(len(levels)))
    ax4.bar([i - width / 2 for i in lvls], total_counts, width=width, label="Total", color="#95a5a6")
    ax4.bar([i + width / 2 for i in lvls], success_counts, width=width, label="Success", color="#2ecc71")
    ax4.set_xticks(lvls)
    ax4.set_xticklabels(levels)
    ax4.set_xlabel("Constraint Level")
    ax4.set_title("Success vs Total by Level", fontsize=12, fontweight="bold")
    ax4.grid(axis="y", alpha=0.3)
    ax4.legend()

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"\n📊 Plot saved to: {save_path}")


# ================= Mode auto-detect and entrypoint ================= #
def detect_mode(input_path: str) -> Tuple[str, Path]:
    p = Path(input_path)
    if p.is_dir():
        # infer directory (contains results.json/summary.json)
        if (p / "results.json").exists() and (p / "summary.json").exists():
            return "infer", p
        # evolution does not take a directory input
    else:
        # JSON file, try evolution first
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and any(isinstance(x, dict) and "creativity_evaluation" in x for x in data):
                return "evolution", p
        except Exception:
            pass
        # If infer results.json
        if p.name == "results.json" and (p.parent / "summary.json").exists():
            return "infer", p.parent
    raise ValueError(f"Unrecognized input. Provide evolution JSON or infer run dir/results.json: {input_path}")


if __name__ == "__main__":
    default_path = "test_results/run_20251001_114825/creativity_evolution_results.json"
    in_path = sys.argv[1] if len(sys.argv) > 1 else default_path

    mode, resolved = detect_mode(in_path)
    if mode == "evolution":
        result_dir = os.path.dirname(str(resolved))
        output_path = os.path.join(result_dir, "creativity_analysis.png")
        problems, level_data = analyze_evolution(str(resolved))
        plot_evolution(problems, level_data, save_path=output_path)

        print("\n" + "=" * 70)
        print("💡 RECOMMENDED FINAL METRICS FOR MODEL COMPARISON")
        print("=" * 70)

    else:  # infer
        run_dir, results, summary = load_infer_run(str(resolved))
        output_path = str(run_dir / "creativity_analysis.png")
        levels, pass_rates, avg_novelty, avg_creativity, sims_base, creats, success_counts, total_counts = analyze_infer(results, summary)
        plot_infer(levels, pass_rates, avg_novelty, avg_creativity, sims_base, creats, success_counts, total_counts, output_path)
