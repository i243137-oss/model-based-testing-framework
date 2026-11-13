# Task: Complete the Model-Based Testing Framework Assignment

You are a senior Python Software Engineer and Software Testing Engineer specializing in Model-Based Testing (MBT), State Machines, Test Automation, Mutation Testing, and Experimental Evaluation.

Your task is to **fully implement the existing student starter code** in this GitHub repository:

Repository: https://github.com/i243137-oss/model-based-testing-framework

The project implements a Model-Based Testing framework for a Smart Parcel Locker Management System.

IMPORTANT: This is a university programming assignment. Follow the provided assignment specification and starter code. Do not turn it into an unnecessarily complex commercial framework.

---

## 1. MOST IMPORTANT: Inspect Before Implementing

Before writing or modifying code:

1. Inspect the entire repository and its directory structure.
2. Read every existing Python module.
3. Read `README.md` and `data/requirements.md`.
4. Inspect the provided reference System Under Test (`locker/sut.py`).
5. Inspect the existing smoke tests and understand their expectations.
6. Identify all TODOs, incomplete implementations, missing functionality, and inconsistencies.
7. Map each assignment requirement to the relevant existing module.

Do not immediately rewrite the project.

**Preserve the provided starter code and its intended architecture.**

The existing reference SUT is part of the assignment. It is the implementation under test, not something you should replace with your own implementation.

---

## 2. Academic and Implementation Rules

Follow these rules throughout development:

- Implement actual working functionality, not pseudocode.
- Do not fabricate test results, coverage percentages, mutation scores, or experimental findings.
- Do not hardcode results just to make the assignment appear complete.
- Do not create fake screenshots, terminal outputs, demonstration recordings, or manually fabricated evidence.
- Do not generate artificial evidence of activities that I am expected to perform and capture myself.
- Do not claim that experiments have been conducted unless they have actually been executed.
- Do not modify the reference SUT to make the tests pass.
- Do not derive expected results by calling the SUT.
- Do not use the SUT's internal fields as the expected model state.
- Do not hide failing tests or weaken assertions.
- Do not delete existing tests simply because they fail.
- Do not add unnecessary dependencies or unrelated features.
- Do not create unnecessary documentation files or duplicate implementations.

When something requires my personal participation, such as screenshots, a demonstration recording, manual report discussion, or instructor-specific information, leave it for me to complete.

You may implement scripts that generate genuine evidence and experimental data when I execute them.

---

## 3. Implement the Independent Executable State Model

File: `locker/model.py`

Implement `LockerModel` independently of the reference SUT.

Required states:

- AVAILABLE
- RESERVED
- OCCUPIED
- MAINTENANCE

Required operations:

- RESERVE
- CANCEL
- DEPOSIT
- RETRIEVE
- EXPIRE
- DISABLE
- ENABLE
- INVALID_ACCESS

Implement:

- State initialization and reset.
- Preconditions and guard conditions.
- Valid and invalid operation handling.
- State transitions.
- Credential management.
- Expected operation results.
- Complete state snapshots.
- State consistency and invariants.

Important behavioural requirements:

- Reservation generates `R-<customer_id>`.
- Successful deposit generates `P-<customer_id>`.
- Deposit requires a valid reservation code.
- Retrieval requires a valid retrieval code.
- Cancellation is permitted only in RESERVED.
- Expiration requires RESERVED and `expired=True`.
- Expiration immediately returns the locker to AVAILABLE.
- Successful cancellation, expiration, and retrieval clear associated information.
- Maintenance can be entered only from AVAILABLE.
- ENABLE returns MAINTENANCE to AVAILABLE.
- Invalid operations and rejected operations must not mutate state.

The model must remain logically independent of `locker/sut.py`.

The model is the source of expected behaviour.

---

## 4. Implement Three Different Test-Generation Strategies

File: `locker/generators.py`

Implement the existing three generator classes.

### Strategy A: Random Walk Generator

`RandomWalkGenerator`

Requirements:

- Generate reproducible random sequences.
- Support configurable random seeds.
- Support configurable maximum sequence lengths.
- Generate both valid and invalid operations.
- Generate appropriate command parameters and credentials.
- Produce independently executable sequences.

### Strategy B: Coverage-Guided Generator

`CoverageGuidedGenerator`

Requirements:

- Prioritize unexplored states.
- Prioritize unexplored transitions.
- Track exploration progress.
- Prefer operations that increase coverage.
- Handle situations where some targets are unreachable.
- Use a seed for reproducibility when random selection is needed.

This must use a genuinely coverage-directed selection mechanism, not simply random generation with a different name.

### Strategy C: Transition-Pair Generator

`TransitionPairGenerator`

Requirements:

- Target consecutive transition pairs.
- Generate sequences that exercise different transition combinations.
- Track which transition pairs have been covered.
- Handle unreachable transition pairs.
- Respect maximum sequence length.

All three strategies must use the independent model and produce compatible command sequences.

They must be algorithmically different.

Document the algorithm, advantages, and limitations of each strategy.

---

## 5. Implement Automated Test Execution and Oracle

File: `locker/runner.py`

Implement `SequenceRunner`.

For every generated sequence:

1. Initialize a fresh reference SUT.
2. Initialize an independent model.
3. Execute each command against both.
4. Compare expected and actual operation results.
5. Compare complete expected and actual snapshots.
6. Check important state invariants.
7. Record the first divergence.
8. Identify the failing command index.
9. Record expected and actual values.
10. Return a structured execution result.

Record at least:

- Test ID.
- Generation strategy.
- Complete command sequence.
- Initial state.
- Expected result.
- Actual result.
- Expected final state.
- Actual final state.
- Pass/fail outcome.
- Failure details.
- Execution time.

Check invariants, including:

- AVAILABLE has no associated customer or credentials.
- RESERVED has appropriate reservation information.
- OCCUPIED has valid parcel retrieval information.
- MAINTENANCE does not contain active reservation information.
- Rejected operations do not mutate the state.
- Unauthorized access does not change credentials.
- Retrieved parcels cannot be retrieved again.

Do not compare only return messages. Complete snapshots and state consistency are essential.

---

## 6. Implement Coverage and Mutation Metrics

File: `locker/metrics.py`

Implement:

### Coverage metrics

- State coverage.
- Transition coverage.
- Transition-pair coverage.

Use clearly defined coverage denominators.

Avoid reporting misleading percentages when a transition is unreachable.

### Mutation metrics

Implement:

- Total mutants.
- Detected mutants.
- Surviving mutants.
- Mutation score.

Use:

Mutation Score = (Detected Mutants / Total Non-Equivalent Mutants) × 100

Handle equivalent or invalid mutants explicitly instead of silently counting them as detected.

---

## 7. Implement Mutation Testing

Create or extend a logically organized mutation-testing module.

The assignment requires evaluation of at least eight faulty system variants.

Introduce at least eight meaningful mutants based on realistic implementation mistakes.

Examples:

- Allow reservation of an occupied locker.
- Accept incorrect reservation credentials.
- Allow retrieval without valid authentication.
- Allow retrieval more than once.
- Allow expiration when `expired=False`.
- Fail to clear credentials after cancellation.
- Allow maintenance while the locker is reserved.
- Allow enabling a locker that is not under maintenance.

Requirements:

1. Keep the original SUT unchanged.
2. Implement mutants as separate faulty implementations or controlled fault-injection variants.
3. Execute the same generated tests against the original SUT and mutants.
4. Identify which tests detect each mutant.
5. Calculate mutation scores.
6. Record mutant-level results.
7. Distinguish surviving, killed, and equivalent mutants.
8. Make experiments reproducible.

Do not simply create eight classes that return predetermined failures. Each mutant must represent a real behavioral defect.

---

## 8. Experimental Evaluation

Implement a proper experiment runner.

Compare all three strategies under controlled conditions.

Include:

- Configurable number of generated tests.
- Configurable maximum sequence length.
- Reproducible random seeds.
- State coverage.
- Transition coverage.
- Transition-pair coverage.
- Mutation score.
- Number of detected mutants.
- Number of surviving mutants.
- Execution time.
- Test pass/fail counts.

Use consistent experimental configurations so comparisons are meaningful.

Save actual results in machine-readable formats such as:

- CSV
- JSON

Create scripts to execute the experiments and reproduce the results.

If appropriate, implement charts generated from actual experimental data.

Never invent experimental values or write conclusions before results exist.

---

## 9. Technical Report Support

The assignment requires a complete technical report.

Prepare a report template or a report-generation mechanism that uses actual experiment outputs.

The report should cover:

1. Introduction.
2. Requirements Analysis.
3. State-Machine Model.
4. Test-Generation Strategies.
5. Test Execution Framework.
6. Mutation Testing.
7. Experimental Setup.
8. Results.
9. Discussion and Limitations.
10. Conclusion.

Important:

- Do not invent experimental findings.
- Do not fabricate screenshots or demonstration evidence.
- Do not create fake observations.
- Leave clearly marked sections for my own manual discussion, screenshots, and demonstration details.
- Populate numerical tables only from genuine generated experiment data.

---

## 10. README and Project Documentation

Update the existing README without unnecessarily replacing its useful content.

Include:

- Project overview.
- Architecture.
- Requirements.
- Python version.
- Installation instructions.
- Dependency installation.
- Running smoke tests.
- Running each generator independently.
- Running the automated test runner.
- Running mutation experiments.
- Running complete experiments.
- Output locations.
- Reproducing experiments using seeds.

Keep documentation accurate to the implemented functionality.

---

## 11. Code Quality Requirements

Follow professional Python practices:

- Meaningful naming.
- Modular architecture.
- Type hints.
- Appropriate dataclasses and enums.
- Clear exception handling.
- Useful docstrings.
- Separation of concerns.
- No unnecessary code duplication.
- No unnecessary dependencies.

Keep the implementation understandable for a university student who must explain the complete project during an individual viva.

Do not introduce advanced abstractions without a clear reason.

---

## 12. Testing and Verification

After implementation:

1. Run all existing smoke tests.
2. Run all existing unit tests.
3. Add meaningful tests for the new functionality.
4. Test valid transitions.
5. Test invalid transitions.
6. Test authentication failures.
7. Test state invariants.
8. Test generator reproducibility.
9. Test coverage calculations.
10. Test mutation detection.
11. Run the complete experimental workflow.
12. Verify that CSV and JSON outputs contain genuine results.

Fix implementation errors rather than weakening tests.

Do not report success if tests have not actually passed.

---

## 13. Final Completion Audit

Before finishing, produce a requirement-by-requirement audit.

Use these statuses:

- IMPLEMENTED AND TESTED
- IMPLEMENTED BUT NOT FULLY VERIFIED
- NOT IMPLEMENTED
- REQUIRES MANUAL STUDENT ACTION

For every requirement, mention:

- Relevant file.
- Implementation details.
- Verification performed.
- Remaining work.

Explicitly identify anything I still need to do manually, particularly:

- Screenshots.
- Demonstration recording.
- Personal report discussion.
- Any required instructor-specific submission details.

Do not pretend these activities have been completed.

---

## Final Instruction

Work directly with the existing repository and starter code.

Prioritize correctness, genuine implementation, reproducibility, and assignment compliance over visual presentation or unnecessary features.

**Do not just provide suggestions or code snippets. Implement the actual project, execute the tests, fix the problems, and provide a final honest completion report.**

I must be able to understand, explain, debug, and modify the implementation during my individual viva.