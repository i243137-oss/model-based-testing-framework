import os
import sys
import time
import json
import csv
import argparse
from typing import Dict, List, Any
import statistics

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from locker.types import State, Operation, Command
from locker.sut import ParcelLocker
from locker.model import LockerModel
from locker.generators import (
    RandomWalkGenerator,
    CoverageGuidedGenerator,
    TransitionPairGenerator,
)
from locker.runner import SequenceRunner
from locker.metrics import calculate_coverage, mutation_summary
from locker.mutants import ALL_MUTANTS, ALL_MUTANT_METADATA, MUTANT_DESCRIPTIONS


def run_strategy_experiment(
    strategy_name: str,
    generator_cls: Any,
    seed: int,
    num_sequences: int,
    max_length: int,
    mutants: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute evaluation for one strategy and one seed."""
    generator = generator_cls(seed=seed, max_length=max_length)

    # 1. Measure test generation time
    gen_start = time.perf_counter()
    sequences: List[List[Command]] = generator.generate(num_sequences)
    generation_time = time.perf_counter() - gen_start

    # 2. Execute on reference SUT
    sut_runner = SequenceRunner(sut_factory=ParcelLocker, model_factory=LockerModel)
    exec_start = time.perf_counter()
    sut_results = sut_runner.run_all(sequences, strategy=strategy_name)
    sut_execution_time = time.perf_counter() - exec_start

    passed_count = sum(1 for r in sut_results if r.passed)
    failed_count = sum(1 for r in sut_results if not r.passed)

    # Collect traces for coverage
    traces = [r.trace for r in sut_results]
    cov_report = calculate_coverage(traces)

    # 3. Mutation Testing
    # Run test suite against each mutant until detected or suite finishes
    mutant_eval: Dict[str, Dict[str, Any]] = {}
    mut_exec_start = time.perf_counter()

    for m_name, m_cls in mutants.items():
        m_runner = SequenceRunner(sut_factory=m_cls, model_factory=LockerModel)
        detected = False
        killing_test = None
        divergence_reason = None

        for r_idx, seq in enumerate(sequences):
            m_res = m_runner.run(seq, test_id=f"{strategy_name}_S{seed}_T{r_idx+1}")
            if not m_res.passed:
                detected = True
                killing_test = m_res.test_id
                divergence_reason = m_res.failure_details
                break

        m_meta = ALL_MUTANT_METADATA.get(m_name)
        is_equiv = m_meta.is_equivalent if m_meta else False
        desc = m_meta.description if m_meta else MUTANT_DESCRIPTIONS.get(m_name, "")
        cat = m_meta.defect_category if m_meta else "General Defect"
        equiv_reason = m_meta.equivalence_rationale if m_meta else "Evaluated as non-equivalent"

        mutant_eval[m_name] = {
            "detected": detected,
            "equivalent": is_equiv,
            "killing_test": killing_test,
            "divergence_reason": divergence_reason,
            "description": desc,
            "defect_category": cat,
            "equivalence_rationale": equiv_reason,
        }

    total_mutation_time = time.perf_counter() - mut_exec_start
    mut_summary = mutation_summary(mutant_eval)

    return {
        "strategy": strategy_name,
        "seed": seed,
        "num_sequences": num_sequences,
        "max_length": max_length,
        "generation_time_sec": generation_time,
        "sut_execution_time_sec": sut_execution_time,
        "mutation_execution_time_sec": total_mutation_time,
        "total_time_sec": generation_time + sut_execution_time + total_mutation_time,
        "sut_passed_tests": passed_count,
        "sut_failed_tests": failed_count,
        "coverage": cov_report.to_dict(),
        "mutation": mut_summary.to_dict(),
    }


def generate_plots(summary_data: Dict[str, Any], output_dir: str):
    """Generate visual comparison charts using matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[Notice] matplotlib not available, skipping chart generation.")
        return

    strategies = list(summary_data.keys())
    x = range(len(strategies))

    # 1. Coverage Metrics Bar Chart
    fig, ax = plt.subplots(figsize=(10, 6))
    bar_width = 0.2
    x1 = [i - 1.5 * bar_width for i in x]
    x2 = [i - 0.5 * bar_width for i in x]
    x3 = [i + 0.5 * bar_width for i in x]
    x4 = [i + 1.5 * bar_width for i in x]

    state_covs = [summary_data[s]["mean_state_cov"] for s in strategies]
    valid_covs = [summary_data[s]["mean_valid_trans_cov"] for s in strategies]
    op_covs = [summary_data[s]["mean_state_op_cov"] for s in strategies]
    pair_covs = [summary_data[s]["mean_pair_cov"] for s in strategies]

    ax.bar(x1, state_covs, width=bar_width, label="State Coverage %", color="#4CAF50")
    ax.bar(x2, valid_covs, width=bar_width, label="Valid Trans %", color="#2196F3")
    ax.bar(x3, op_covs, width=bar_width, label="State-Op Cov %", color="#FF9800")
    ax.bar(x4, pair_covs, width=bar_width, label="Trans-Pair %", color="#9C27B0")

    ax.set_xticks(list(x))
    ax.set_xticklabels(strategies, fontsize=11, fontweight="bold")
    ax.set_ylabel("Coverage Percentage (%)", fontsize=11)
    ax.set_title("Coverage Comparison Across Test Generation Strategies", fontsize=13, fontweight="bold")
    ax.set_ylim(0, 110)
    ax.legend(loc="lower right")
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "coverage_comparison.png"), dpi=200)
    plt.close()

    # 2. Mutation Score Comparison
    fig, ax = plt.subplots(figsize=(8, 5))
    scores = [summary_data[s]["mean_mutation_score"] for s in strategies]
    stds = [summary_data[s]["std_mutation_score"] for s in strategies]
    colors = ["#2196F3", "#4CAF50", "#FF9800"]

    bars = ax.bar(strategies, scores, yerr=stds, capsize=5, color=colors, width=0.5)
    ax.set_ylabel("Mutation Score (%)", fontsize=11)
    ax.set_title("Mutation Score Comparison", fontsize=13, fontweight="bold")
    ax.set_ylim(0, 115)
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f"{height:.1f}%",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 4), textcoords="offset points",
                    ha="center", va="bottom", fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "mutation_score_comparison.png"), dpi=200)
    plt.close()

    # 3. Execution Time Comparison
    fig, ax = plt.subplots(figsize=(8, 5))
    gen_times = [summary_data[s]["mean_generation_time"] for s in strategies]
    sut_times = [summary_data[s]["mean_sut_exec_time"] for s in strategies]

    b1 = ax.bar(strategies, gen_times, label="Test Generation Time", color="#00BCD4", width=0.45)
    b2 = ax.bar(strategies, sut_times, bottom=gen_times, label="SUT Execution Time", color="#3F51B5", width=0.45)
    ax.set_ylabel("Time (seconds)", fontsize=11)
    ax.set_title("Time Breakdown (Generation + Execution)", fontsize=13, fontweight="bold")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "execution_time_comparison.png"), dpi=200)
    plt.close()

    print(f"[Info] Plots generated successfully in {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Model-Based Testing Experimental Evaluation Runner")
    parser.add_argument("--sequences", type=int, default=500, help="Number of test sequences per strategy")
    parser.add_argument("--max-length", type=int, default=20, help="Maximum length per sequence")
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=[101, 202, 303, 404, 505],
        help="Random seeds for stochastic evaluations",
    )
    parser.add_argument("--output-dir", type=str, default="results", help="Directory to save experimental results")
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    strategy_map = {
        "RandomWalk": RandomWalkGenerator,
        "CoverageGuided": CoverageGuidedGenerator,
        "TransitionPair": TransitionPairGenerator,
    }

    print("=" * 78)
    print("STARTING CONTROLLED EXPERIMENTAL EVALUATION")
    print(f"Configurations: Sequences={args.sequences}, Max-Length={args.max_length}")
    print(f"Seeds: {args.seeds}")
    print(f"Target Mutants: {len(ALL_MUTANTS)} mutants")
    print("=" * 78)

    all_raw_runs: List[Dict[str, Any]] = []

    for strat_name, gen_cls in strategy_map.items():
        print(f"\nEvaluating Strategy: {strat_name}...")
        for seed in args.seeds:
            print(f"  -> Running seed {seed}...", end=" ", flush=True)
            res = run_strategy_experiment(
                strategy_name=strat_name,
                generator_cls=gen_cls,
                seed=seed,
                num_sequences=args.sequences,
                max_length=args.max_length,
                mutants=ALL_MUTANTS,
            )
            all_raw_runs.append(res)
            print(
                f"Done. StateCov: {res['coverage']['state_coverage_pct']}% | "
                f"ValidTransCov: {res['coverage']['valid_transition_coverage_pct']}% | "
                f"MutScore: {res['mutation']['mutation_score']}%"
            )

    # Save complete raw runs JSON
    raw_json_path = os.path.join(output_dir, "raw_experiment_results.json")
    with open(raw_json_path, "w", encoding="utf-8") as f:
        json.dump(all_raw_runs, f, indent=2)

    # Compute aggregated metrics across seeds
    summary_by_strategy: Dict[str, Any] = {}
    for strat_name in strategy_map.keys():
        runs = [r for r in all_raw_runs if r["strategy"] == strat_name]

        state_covs = [r["coverage"]["state_coverage_pct"] for r in runs]
        valid_covs = [r["coverage"]["valid_transition_coverage_pct"] for r in runs]
        state_op_covs = [r["coverage"]["state_operation_coverage_pct"] for r in runs]
        pair_covs = [r["coverage"]["transition_pair_coverage_pct"] for r in runs]
        mut_scores = [r["mutation"]["mutation_score"] for r in runs]
        detected_counts = [r["mutation"]["detected_mutants"] for r in runs]
        gen_times = [r["generation_time_sec"] for r in runs]
        sut_exec_times = [r["sut_execution_time_sec"] for r in runs]
        mut_exec_times = [r["mutation_execution_time_sec"] for r in runs]

        summary_by_strategy[strat_name] = {
            "mean_state_cov": round(statistics.mean(state_covs), 2),
            "mean_valid_trans_cov": round(statistics.mean(valid_covs), 2),
            "mean_state_op_cov": round(statistics.mean(state_op_covs), 2),
            "mean_pair_cov": round(statistics.mean(pair_covs), 2),
            "mean_mutation_score": round(statistics.mean(mut_scores), 2),
            "std_mutation_score": round(statistics.stdev(mut_scores) if len(mut_scores) > 1 else 0.0, 2),
            "mean_detected_mutants": round(statistics.mean(detected_counts), 2),
            "mean_generation_time": round(statistics.mean(gen_times), 4),
            "mean_sut_exec_time": round(statistics.mean(sut_exec_times), 4),
            "mean_mut_exec_time": round(statistics.mean(mut_exec_times), 4),
        }

    # Save summary JSON
    summary_json_path = os.path.join(output_dir, "experiments_summary.json")
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_by_strategy, f, indent=2)

    # Export CSV: Strategy Comparison Table
    comparison_csv_path = os.path.join(output_dir, "strategy_comparison.csv")
    with open(comparison_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Strategy",
            "Mean State Coverage (%)",
            "Mean Valid Trans Coverage (%)",
            "Mean State-Op Coverage (%)",
            "Mean Transition-Pair Coverage (%)",
            "Mean Mutation Score (%)",
            "Std Mutation Score",
            "Mean Detected Mutants (out of 10)",
            "Mean Gen Time (s)",
            "Mean SUT Exec Time (s)",
            "Mean Mut Exec Time (s)",
        ])
        for strat, data in summary_by_strategy.items():
            writer.writerow([
                strat,
                data["mean_state_cov"],
                data["mean_valid_trans_cov"],
                data["mean_state_op_cov"],
                data["mean_pair_cov"],
                data["mean_mutation_score"],
                data["std_mutation_score"],
                data["mean_detected_mutants"],
                data["mean_generation_time"],
                data["mean_sut_exec_time"],
                data["mean_mut_exec_time"],
            ])

    # Export CSV: Mutant Detection Matrix
    mutant_matrix_csv = os.path.join(output_dir, "mutant_detection_matrix.csv")
    with open(mutant_matrix_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["Mutant Name", "Defect Category", "Equivalent", "Defect Description"] + list(strategy_map.keys())
        writer.writerow(header)

        for m_name in ALL_MUTANTS.keys():
            m_meta = ALL_MUTANT_METADATA.get(m_name)
            cat = m_meta.defect_category if m_meta else "General"
            is_equiv = "Yes" if (m_meta and m_meta.is_equivalent) else "No"
            desc = m_meta.description if m_meta else MUTANT_DESCRIPTIONS.get(m_name, "")

            row = [m_name, cat, is_equiv, desc]
            for strat in strategy_map.keys():
                strat_runs = [r for r in all_raw_runs if r["strategy"] == strat]
                # Proportion of seeds that detected this mutant
                det_ratio = sum(1 for r in strat_runs if r["mutation"]["mutant_details"][m_name]["detected"]) / len(strat_runs)
                row.append(f"{det_ratio * 100:.0f}%")
            writer.writerow(row)

    # Generate charts
    generate_plots(summary_by_strategy, output_dir)

    # Print summary table
    print("\n" + "=" * 90)
    print("EXPERIMENTAL EVALUATION SUMMARY (Averaged over 5 Seeds)")
    print("=" * 90)
    print(f"{'Strategy':<18} | {'State%':<7} | {'ValidTrans%':<12} | {'StateOp%':<9} | {'PairCov%':<9} | {'MutScore%':<10} | {'GenTime(s)':<11} | {'SUTTime(s)':<10}")
    print("-" * 90)
    for strat, data in summary_by_strategy.items():
        print(
            f"{strat:<18} | "
            f"{data['mean_state_cov']:<7.1f} | "
            f"{data['mean_valid_trans_cov']:<12.1f} | "
            f"{data['mean_state_op_cov']:<9.1f} | "
            f"{data['mean_pair_cov']:<9.1f} | "
            f"{data['mean_mutation_score']:<10.1f} | "
            f"{data['mean_generation_time']:<11.4f} | "
            f"{data['mean_sut_exec_time']:<10.4f}"
        )
    print("=" * 90)
    print(f"Results and charts saved in directory: {output_dir}\n")


if __name__ == "__main__":
    main()
