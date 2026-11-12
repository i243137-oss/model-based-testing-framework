# Student Starter: Smart Parcel Locker MBT

Python 3.10+. Run the supplied smoke tests with:
`python -m unittest discover -s tests -v`

## Structure
- `locker/sut.py`: provided reference System Under Test (SUT).
- `locker/types.py`: states, operations, commands, results, snapshots.
- `locker/model.py`: TODO — independent executable oracle.
- `locker/generators.py`: TODO — three test-generation strategies.
- `locker/runner.py`: TODO — automated execution and comparison.
- `locker/metrics.py`: TODO — coverage and mutation metrics.
- `data/requirements.md`: behavioural requirements.

## Student responsibilities
Implement the TODO modules. Your framework must:
1. Model expected behaviour independently of the SUT.
2. Generate valid and invalid operation sequences using at least three strategies.
3. Execute sequences and compare results AND complete snapshots.
4. Measure state, transition, and transition-pair coverage.
5. Support reproducible random seeds and configurable sequence lengths.
6. Export experiment results to CSV or JSON.

Do not call the SUT from your model or inspect its internal fields. Derive the model independently from the requirements.

The reference SUT is provided; the generator, model, runner, metrics, experiments, and analysis are student work. Your instructor may introduce unseen variants during the viva.
