import unittest
from locker.runner import SequenceRunner
from locker.sut import ParcelLocker
from locker.model import LockerModel
from locker.types import Command, Operation, State, Result, Snapshot
from locker.mutants import Mutant1_ReserveOccupied, Mutant2_AcceptWrongReservationCode, Mutant6_CancelRetainsCredentials, Mutant10_MutateOnInvalidDeposit


class CrashingSUT(ParcelLocker):
    """SUT variant that raises an unexpected exception during execution."""
    def execute(self, command: Command) -> Result:
        if command.operation == Operation.DEPOSIT:
            raise RuntimeError("Database hardware failure")
        return super().execute(command)


class CorruptMultiViolationSUT(ParcelLocker):
    """SUT variant that simultaneously triggers Result divergence, Snapshot divergence,

    and Domain invariant violation on the same step.
    """
    def execute(self, command: Command) -> Result:
        if command.operation == Operation.RESERVE:
            # Corrupt state: sets state to AVAILABLE with leftover customer_id
            self.state = State.AVAILABLE
            self.customer_id = "ILLEGAL_CUST"
            self.reservation_code = "ILLEGAL_CODE"
            return Result(False, "corrupted_failure")
        return super().execute(command)


class TestSequenceRunner(unittest.TestCase):
    def setUp(self):
        self.runner = SequenceRunner()

    def test_run_valid_sequence_passes(self):
        seq = [
            Command(Operation.RESERVE, customer_id="C1"),
            Command(Operation.DEPOSIT, customer_id="C1", code="R-C1"),
            Command(Operation.RETRIEVE, customer_id="C1", code="P-C1"),
        ]
        res = self.runner.run(seq, test_id="T_VALID", strategy="Manual")
        self.assertTrue(res.passed)
        self.assertIsNone(res.failure_step)
        self.assertEqual(res.expected_final_state, State.AVAILABLE)
        self.assertEqual(res.actual_final_state, State.AVAILABLE)
        self.assertEqual(len(res.trace), 3)

    def test_run_detects_mutant_divergence(self):
        faulty_runner = SequenceRunner(sut_factory=Mutant2_AcceptWrongReservationCode)
        seq = [
            Command(Operation.RESERVE, customer_id="C1"),
            Command(Operation.DEPOSIT, customer_id="C1", code="BAD_CODE"),
        ]
        res = faulty_runner.run(seq, test_id="T_MUTANT2", strategy="Manual")
        self.assertFalse(res.passed)
        self.assertEqual(res.failure_step, 1)
        self.assertIn("Result divergence", res.failure_details)

    def test_multi_violation_diagnostic_reporting(self):
        """Verify that when multiple checks fail on a single step, all violations

        are independently recorded rather than one hiding another.
        """
        multi_runner = SequenceRunner(sut_factory=CorruptMultiViolationSUT)
        seq = [Command(Operation.RESERVE, customer_id="C1")]
        res = multi_runner.run(seq, test_id="T_MULTI")
        self.assertFalse(res.passed)
        self.assertEqual(res.failure_step, 0)

        # Check that failure_details contains Result divergence, Snapshot divergence, AND Domain invariant violation
        self.assertIn("Result divergence", res.failure_details)
        self.assertIn("Snapshot divergence", res.failure_details)
        self.assertIn("Domain invariant violation", res.failure_details)

        # In step_records, all violations must be listed
        violations = res.step_records[0].violations
        self.assertGreaterEqual(len(violations), 3)

    def test_sut_exception_reporting(self):
        """Verify that exceptions raised by SUT are captured clearly in diagnostics."""
        crash_runner = SequenceRunner(sut_factory=CrashingSUT)
        seq = [
            Command(Operation.RESERVE, customer_id="C1"),
            Command(Operation.DEPOSIT, customer_id="C1", code="R-C1"),
        ]
        res = crash_runner.run(seq, test_id="T_CRASH")
        self.assertFalse(res.passed)
        self.assertEqual(res.failure_step, 1)
        self.assertIn("EXCEPTION_RuntimeError", res.failure_details)
        self.assertIn("Database hardware failure", res.failure_details)

    def test_non_mutation_invariant_detection(self):
        """Verify that rejected operations that mutate SUT are reported with non-mutation invariant violation."""
        faulty_runner = SequenceRunner(sut_factory=Mutant10_MutateOnInvalidDeposit)
        seq = [
            Command(Operation.RESERVE, customer_id="C1"),
            Command(Operation.DEPOSIT, customer_id="C1", code="WRONG_CODE"),
        ]
        res = faulty_runner.run(seq, test_id="T_NON_MUT")
        self.assertFalse(res.passed)
        self.assertEqual(res.failure_step, 1)
        self.assertIn("Non-mutation invariant violation", res.failure_details)

    def test_credential_cleanup_invariant_detection(self):
        """Verify that successful cancellation that retains credentials triggers cleanup violation."""
        faulty_runner = SequenceRunner(sut_factory=Mutant6_CancelRetainsCredentials)
        seq = [
            Command(Operation.RESERVE, customer_id="C1"),
            Command(Operation.CANCEL),
        ]
        res = faulty_runner.run(seq, test_id="T_CLEANUP")
        self.assertFalse(res.passed)
        self.assertEqual(res.failure_step, 1)
        self.assertIn("Cleanup invariant violation", res.failure_details)

    def test_run_all_batch(self):
        seqs = [
            [Command(Operation.DISABLE), Command(Operation.ENABLE)],
            [Command(Operation.RESERVE, customer_id="C2"), Command(Operation.CANCEL)],
        ]
        results = self.runner.run_all(seqs, strategy="TestStrategy")
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.passed for r in results))

    def test_divergence_midway_failure_state_reporting(self):
        """Verify that when divergence occurs midway through a sequence:

        1. The runner halts execution immediately at the divergence step.
        2. failure_step correctly identifies the divergence index.
        3. expected_state_at_failure and actual_state_at_failure accurately record
           states at that exact failure point.
        4. Backward-compatible aliases expected_final_state and actual_final_state match.
        """
        # Mutant 2 accepts bad reservation code during DEPOSIT (step 1)
        faulty_runner = SequenceRunner(sut_factory=Mutant2_AcceptWrongReservationCode)
        long_seq = [
            Command(Operation.RESERVE, customer_id="C1"),
            Command(Operation.DEPOSIT, customer_id="C1", code="BAD_CODE"),  # Divergence here (step 1)
            Command(Operation.RETRIEVE, customer_id="C1", code="P-C1"),    # Should NOT be reached
            Command(Operation.DISABLE),                                     # Should NOT be reached
            Command(Operation.ENABLE),                                      # Should NOT be reached
        ]
        res = faulty_runner.run(long_seq, test_id="T_MIDWAY")
        self.assertFalse(res.passed)
        self.assertEqual(res.failure_step, 1)

        # Runner must halt on step 1: exactly 2 step records recorded (steps 0 and 1)
        self.assertEqual(len(res.step_records), 2)
        self.assertEqual(len(res.trace), 2)

        # State reporting at failure:
        # Expected model rejected deposit -> remained in RESERVED
        # Actual faulty mutant accepted deposit -> transitioned to OCCUPIED
        self.assertEqual(res.expected_state_at_failure, State.RESERVED)
        self.assertEqual(res.actual_state_at_failure, State.OCCUPIED)

        # Check backward-compatibility property aliases
        self.assertEqual(res.expected_final_state, State.RESERVED)
        self.assertEqual(res.actual_final_state, State.OCCUPIED)


if __name__ == "__main__":
    unittest.main()
