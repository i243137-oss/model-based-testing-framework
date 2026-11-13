# Smart Parcel Locker: Model-Based Testing Framework

An end-to-end, academic-grade Model-Based Testing (MBT) framework for a Smart Parcel Locker Management System. This project implements an independent executable state model, three distinct automated test-generation algorithms, an automated dual-oracle execution engine with state-invariant checking, 10 realistic implementation mutants, and an experimental evaluation pipeline.

---

## 1. System Architecture

```
model-based-testing-framework/
├── Assignment Statemachine.pdf   # Official assignment specification
├── instructions.md               # Detailed academic implementation requirements
├── README.md                     # Framework documentation & run instructions
├── report.md                     # Full Technical Report with experimental findings
├── data/
│   └── requirements.md           # Formal behavioral requirements & assumptions
├── locker/                       # Core MBT Framework Package
│   ├── __init__.py               # Package exports
│   ├── types.py                  # States, operations, commands, results, snapshots
│   ├── sut.py                    # Reference System Under Test (SUT)
│   ├── model.py                  # Independent executable state-machine oracle
│   ├── generators.py             # RandomWalk, CoverageGuided, TransitionPair generators
│   ├── runner.py                 # SequenceRunner dual-oracle execution engine
│   ├── metrics.py                # State, transition, pair coverage & mutation metrics
│   └── mutants.py                # 10 realistic faulty system implementations
├── tests/                        # Comprehensive Unit & Smoke Test Suite
│   ├── test_sut_smoke.py         # Starter smoke tests
│   ├── test_model.py             # Model state, transitions, guards & invariants tests
│   ├── test_generators.py        # Generator reproducibility & validity tests
│   ├── test_runner.py            # Execution engine & divergence detection tests
│   ├── test_metrics.py           # Coverage & mutation calculation tests
│   └── test_mutants.py           # Verification of all 10 mutant defect exposures
├── experiments/                  # Experimental Evaluation Suite
│   └── run_experiments.py       # Controlled 5-seed, 3-strategy evaluation script
└── results/                      # Generated Experimental Data & Charts
    ├── raw_experiment_results.json
    ├── experiments_summary.json
    ├── strategy_comparison.csv
    ├── mutant_detection_matrix.csv
    ├── coverage_comparison.png
    ├── mutation_score_comparison.png
    └── execution_time_comparison.png
```

---

## 2. Environment & Prerequisites

- **Python Version**: Python 3.10+ (tested on Python 3.10 and 3.11/3.12/3.13)
- **Standard Library Modules**: `dataclasses`, `enum`, `random`, `time`, `json`, `csv`, `argparse`, `statistics`, `unittest`.
- **Optional Visualization Dependencies**: `matplotlib` (used automatically if available to render PNG charts in `results/`).

### Quick Setup

Clone the repository and install visualization dependencies (optional):

```bash
pip install matplotlib pandas
```

---

## 3. How to Run the Tests

### 3.1 Run All Unit Tests and Smoke Tests

To run the complete test suite (41 tests across 6 test modules):

```bash
python -m unittest discover -s tests -v
```

All tests execute inside the local environment without external servers or network access.

### 3.2 Run Individual Test Modules

```bash
# Run SUT smoke tests
python -m unittest tests/test_sut_smoke.py -v

# Run executable state model tests
python -m unittest tests/test_model.py -v

# Run generator reproducibility tests
python -m unittest tests/test_generators.py -v

# Run runner and oracle tests
python -m unittest tests/test_runner.py -v

# Run coverage and mutation metric tests
python -m unittest tests/test_metrics.py -v

# Run mutant fault-exposure verification tests
python -m unittest tests/test_mutants.py -v
```

---

## 4. Running Test Generators Independently

You can interactively instantiate and run any generator from Python:

```python
from locker.generators import RandomWalkGenerator, CoverageGuidedGenerator, TransitionPairGenerator

# Strategy A: Random Walk
gen_a = RandomWalkGenerator(seed=42, max_length=15)
sequences_a = gen_a.generate(count=5)
print(f"Generated {len(sequences_a)} random walk sequences.")

# Strategy B: Coverage Guided
gen_b = CoverageGuidedGenerator(seed=42, max_length=15)
sequences_b = gen_b.generate(count=5)
print(f"Generated {len(sequences_b)} coverage-guided sequences.")

# Strategy C: Transition Pair
gen_c = TransitionPairGenerator(seed=42, max_length=15)
sequences_c = gen_c.generate(count=5)
print(f"Generated {len(sequences_c)} transition-pair sequences.")
```

---

## 5. Running the Automated Test Runner & Oracle

Execute generated sequences against the reference SUT and independent model:

```python
from locker.generators import CoverageGuidedGenerator
from locker.runner import SequenceRunner
from locker.metrics import calculate_coverage

# Generate test sequences
gen = CoverageGuidedGenerator(seed=101, max_length=20)
sequences = gen.generate(count=100)

# Execute via runner
runner = SequenceRunner()
results = runner.run_all(sequences, strategy="CoverageGuided")

# Calculate coverage report
traces = [r.trace for r in results]
report = calculate_coverage(traces)
print(report.to_dict())
```

---

## 6. Running Controlled Experiments

The experiment runner conducts controlled comparisons across all 3 strategies using 5 random seeds (total 7,500 executed test sequences against the SUT and 10 mutants):

```bash
# Run standard experimental protocol (500 sequences, max length 20, 5 seeds)
python experiments/run_experiments.py --sequences 500 --max-length 20 --seeds 101 202 303 404 505 --output-dir results
```

For a rapid verification run:
```bash
python experiments/run_experiments.py --sequences 20 --max-length 15 --seeds 42 101 --output-dir results
```

### Outputs Generated in `results/`:
- `strategy_comparison.csv`: Summary metrics across strategies.
- `mutant_detection_matrix.csv`: Detailed detection percentages for each mutant.
- `experiments_summary.json`: Machine-readable summary statistics.
- `raw_experiment_results.json`: Full per-seed raw telemetry data.
- `coverage_comparison.png`: Visual comparison of State, Valid Transition, State-Operation, and Transition-Pair coverage.
- `mutation_score_comparison.png`: Mutation score comparison with error bars.
- `execution_time_comparison.png`: Breakdown of test generation vs execution latency.

---

## 7. Viva and Unseen Requirement Preparation

The framework is structured so that you can easily adapt to unseen requirements during your viva:
- **To add a new state or transition**: Update `State` and `Operation` in `locker/types.py`, add transition rules and guard checks in `locker/model.py`, and update invariants in `LockerModel.verify_invariants`.
- **To add an unseen mutant**: Create a new subclass of `ParcelLocker` in `locker/mutants.py` overriding `execute()` and register it in `ALL_MUTANTS`.
