import unittest
from locker.generators import (
    RandomWalkGenerator,
    CoverageGuidedGenerator,
    TransitionPairGenerator,
)
from locker.types import Command, Operation, State
from locker.model import LockerModel
from locker.runner import SequenceRunner
from locker.metrics import calculate_coverage, VALID_TRANSITION_PAIRS, is_valid_transition_pair


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
        gen1 = TransitionPairGenerator(seed=789, max_length=15, invalid_prob=0.25)
        seqs1 = gen1.generate(4)

        gen2 = TransitionPairGenerator(seed=789, max_length=15, invalid_prob=0.25)
        seqs2 = gen2.generate(4)

        self.assertEqual(len(seqs1), 4)
        self.assertEqual(seqs1, seqs2)

    def test_transition_pair_different_seeds(self):
        gen1 = TransitionPairGenerator(seed=101, max_length=15)
        gen2 = TransitionPairGenerator(seed=202, max_length=15)
        seqs1 = gen1.generate(3)
        seqs2 = gen2.generate(3)
        self.assertNotEqual(seqs1, seqs2)

    def test_configurable_sequence_lengths_and_constraints(self):
        for target_length in [1, 2, 5, 10, 20]:
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

        self.assertGreater(accepted_count, 0, "RandomWalk must produce valid operations")
        self.assertGreater(rejected_count, 0, "RandomWalk must produce invalid/rejected operations")

    def test_coverage_guided_prioritizes_exploration(self):
        gen = CoverageGuidedGenerator(seed=101, max_length=20)
        seqs = gen.generate(10)

        runner = SequenceRunner()
        results = runner.run_all(seqs, strategy="CoverageGuided")
        traces = [r.trace for r in results]
        report = calculate_coverage(traces)

        self.assertEqual(report.state_coverage_pct, 100.0)
        self.assertGreaterEqual(report.valid_transition_coverage_pct, 85.0)

    # -------------------------------------------------------------
    # In-depth TransitionPairGenerator Specific Behavioral Tests
    # -------------------------------------------------------------

    def test_transition_pair_invalid_operation_generation(self):
        """Test A: Verify that invalid operations genuinely appear in generated sequences

        and contain meaningful invalid parameters.
        """
        gen = TransitionPairGenerator(seed=303, max_length=20, invalid_prob=0.30)
        seqs = gen.generate(10)

        model = LockerModel()
        rejected_count = 0
        meaningful_invalids = []

        for seq in seqs:
            model.reset()
            for cmd in seq:
                res = model.step(cmd)
                if not res.accepted:
                    rejected_count += 1
                    meaningful_invalids.append(cmd)

        self.assertGreater(rejected_count, 0, "TransitionPairGenerator with invalid_prob>0 must generate rejected operations")

        # Verify that meaningful invalid parameters exist among the generated invalid operations
        has_bad_code = any(
            c.operation in (Operation.DEPOSIT, Operation.RETRIEVE) and ("WRONG" in c.code or "BAD" in c.code)
            for c in meaningful_invalids
        )
        has_unexpired = any(
            c.operation == Operation.EXPIRE and not c.expired
            for c in meaningful_invalids
        )
        has_illegal_state_op = any(
            c.operation in (Operation.CANCEL, Operation.ENABLE, Operation.DISABLE, Operation.INVALID_ACCESS)
            for c in meaningful_invalids
        )
        self.assertTrue(has_bad_code or has_unexpired or has_illegal_state_op,
                        "Generated invalid operations must include meaningful negative parameter cases")

    def test_transition_pair_negative_prob_configuration(self):
        """Test E: Verify that invalid_prob configuration is strictly respected."""
        # Case 1: invalid_prob = 0.0 -> zero invalid operations
        gen_zero = TransitionPairGenerator(seed=42, max_length=15, invalid_prob=0.0)
        seqs_zero = gen_zero.generate(5)
        model = LockerModel()
        for seq in seqs_zero:
            model.reset()
            for cmd in seq:
                res = model.step(cmd)
                self.assertTrue(res.accepted, "With invalid_prob=0.0, all generated commands should be valid")

        # Case 2: invalid_prob = 1.0 -> all invalid operations
        gen_full = TransitionPairGenerator(seed=42, max_length=10, invalid_prob=1.0)
        seqs_full = gen_full.generate(3)
        for seq in seqs_full:
            model.reset()
            for cmd in seq:
                res = model.step(cmd)
                self.assertFalse(res.accepted, "With invalid_prob=1.0, all generated commands should be invalid")

    def test_transition_pair_valid_pairs_connected_and_genuine(self):
        """Test B: Verify that generated valid transition pairs are strictly connected."""
        gen = TransitionPairGenerator(seed=404, max_length=20, invalid_prob=0.15)
        seqs = gen.generate(20)

        runner = SequenceRunner()
        results = runner.run_all(seqs, strategy="TransitionPair")
        traces = [r.trace for r in results]
        report = calculate_coverage(traces)

        # Every recorded pair must satisfy is_valid_transition_pair
        for t1, t2 in report.covered_transition_pairs:
            self.assertTrue(is_valid_transition_pair(t1, t2))
            self.assertEqual(t1[2], t2[0], f"Pair ({t1}, {t2}) is disconnected: target != source")

        # Must achieve substantial transition-pair coverage
        self.assertGreaterEqual(report.transition_pair_coverage_pct, 60.0)

    def test_transition_pair_chain_reset_on_rejected_operation(self):
        """Test C: Verify that a rejected operation breaks the transition-pair chain

        and subsequent valid operations start a new chain cleanly.
        """
        # Execute:
        # Step 1: AVAILABLE -> RESERVE -> RESERVED (t1, accepted)
        # Step 2: In RESERVED, attempt DEPOSIT with WRONG_CODE (rejected, breaks chain)
        # Step 3: In RESERVED, attempt DEPOSIT with R-C1 (accepted, t2)
        # Step 4: In OCCUPIED, attempt RETRIEVE with P-C1 (accepted, t3) -> forms pair (t2, t3)
        trace = [
            (State.AVAILABLE, Command(Operation.RESERVE, customer_id="C1"), True, State.RESERVED),
            (State.RESERVED, Command(Operation.DEPOSIT, code="WRONG_CODE"), False, State.RESERVED),
            (State.RESERVED, Command(Operation.DEPOSIT, code="R-C1"), True, State.OCCUPIED),
            (State.OCCUPIED, Command(Operation.RETRIEVE, code="P-C1"), True, State.AVAILABLE),
        ]
        report = calculate_coverage([trace])

        # Pair (t1, t2) must NOT be recorded because step 2 broke the consecutive chain!
        t1 = (State.AVAILABLE, Operation.RESERVE, State.RESERVED)
        t2 = (State.RESERVED, Operation.DEPOSIT, State.OCCUPIED)
        t3 = (State.OCCUPIED, Operation.RETRIEVE, State.AVAILABLE)

        self.assertNotIn((t1, t2), report.covered_transition_pairs)
        # But consecutive valid transitions t2 and t3 (steps 3 and 4) MUST form pair (t2, t3)
        self.assertIn((t2, t3), report.covered_transition_pairs)
        self.assertEqual(len(report.covered_transition_pairs), 1)


if __name__ == "__main__":
    unittest.main()
