import unittest
from locker.generators import (
    RandomWalkGenerator,
    CoverageGuidedGenerator,
    TransitionPairGenerator,
)
from locker.types import Command, Operation, State
from locker.model import LockerModel
from locker.runner import SequenceRunner
from locker.metrics import calculate_coverage, VALID_TRANSITION_PAIRS


class TestGenerators(unittest.TestCase):
    def test_random_walk_reproducibility(self):
        gen1 = RandomWalkGenerator(seed=123, max_length=15)
        seqs1 = gen1.generate(5)

        gen2 = RandomWalkGenerator(seed=123, max_length=15)
        seqs2 = gen2.generate(5)

        self.assertEqual(len(seqs1), 5)
        self.assertEqual(len(seqs2), 5)
        self.assertEqual(seqs1, seqs2)

    def test_random_walk_different_seeds(self):
        gen1 = RandomWalkGenerator(seed=123, max_length=15)
        gen2 = RandomWalkGenerator(seed=999, max_length=15)
        seqs1 = gen1.generate(3)
        seqs2 = gen2.generate(3)
        self.assertNotEqual(seqs1, seqs2)

    def test_coverage_guided_reproducibility(self):
        gen1 = CoverageGuidedGenerator(seed=456, max_length=12)
        seqs1 = gen1.generate(4)

        gen2 = CoverageGuidedGenerator(seed=456, max_length=12)
        seqs2 = gen2.generate(4)

        self.assertEqual(len(seqs1), 4)
        self.assertEqual(seqs1, seqs2)

    def test_transition_pair_reproducibility(self):
        gen1 = TransitionPairGenerator(seed=789, max_length=15)
        seqs1 = gen1.generate(4)

        gen2 = TransitionPairGenerator(seed=789, max_length=15)
        seqs2 = gen2.generate(4)

        self.assertEqual(len(seqs1), 4)
        self.assertEqual(seqs1, seqs2)

    def test_configurable_sequence_lengths(self):
        for target_length in [5, 10, 20]:
            for GenCls in [RandomWalkGenerator, CoverageGuidedGenerator, TransitionPairGenerator]:
                gen = GenCls(seed=42, max_length=target_length)
                seqs = gen.generate(3)
                self.assertEqual(len(seqs), 3)
                for seq in seqs:
                    self.assertEqual(len(seq), target_length)

    def test_command_structure_and_parameters(self):
        for GenCls in [RandomWalkGenerator, CoverageGuidedGenerator, TransitionPairGenerator]:
            gen = GenCls(seed=42, max_length=10)
            seqs = gen.generate(2)
            for seq in seqs:
                for cmd in seq:
                    self.assertIsInstance(cmd, Command)
                    self.assertIsInstance(cmd.operation, Operation)
                    self.assertIsInstance(cmd.customer_id, str)
                    self.assertIsInstance(cmd.code, str)
                    self.assertIsInstance(cmd.expired, bool)
                    self.assertGreater(len(cmd.customer_id), 0)

    def test_random_walk_exercises_valid_and_invalid_operations(self):
        gen = RandomWalkGenerator(seed=42, max_length=20)
        seqs = gen.generate(15)

        model = LockerModel()
        accepted_count = 0
        rejected_count = 0

        for seq in seqs:
            model.reset()
            for cmd in seq:
                res = model.step(cmd)
                if res.accepted:
                    accepted_count += 1
                else:
                    rejected_count += 1

        # Both valid operations and rejected/fuzzed operations must occur
        self.assertGreater(accepted_count, 0, "RandomWalk must produce valid operations")
        self.assertGreater(rejected_count, 0, "RandomWalk must produce invalid/rejected operations")

    def test_coverage_guided_prioritizes_exploration(self):
        # CoverageGuided should rapidly visit all states and unexercised transitions
        gen = CoverageGuidedGenerator(seed=101, max_length=20)
        seqs = gen.generate(10)

        runner = SequenceRunner()
        results = runner.run_all(seqs, strategy="CoverageGuided")
        traces = [r.trace for r in results]
        report = calculate_coverage(traces)

        # Within 10 sequences, CoverageGuided should reach 100% state coverage
        self.assertEqual(report.state_coverage_pct, 100.0)
        # And high valid transition coverage
        self.assertGreaterEqual(report.valid_transition_coverage_pct, 85.0)

    def test_transition_pair_generator_targets_connected_pairs(self):
        gen = TransitionPairGenerator(seed=202, max_length=20)
        seqs = gen.generate(20)

        runner = SequenceRunner()
        results = runner.run_all(seqs, strategy="TransitionPair")
        traces = [r.trace for r in results]
        report = calculate_coverage(traces)

        # Ensure covered pairs are strictly subsets of VALID_TRANSITION_PAIRS
        for pair in report.covered_transition_pairs:
            self.assertIn(pair, VALID_TRANSITION_PAIRS)
            # Connectivity check: t1.target_state == t2.source_state
            t1, t2 = pair
            self.assertEqual(t1[2], t2[0])

        # Over 20 sequences of length 20, it should cover majority of the 13 pairs
        self.assertGreaterEqual(len(report.covered_transition_pairs), 8)


if __name__ == "__main__":
    unittest.main()
