import unittest
from locker.runner import SequenceRunner
from locker.sut import ParcelLocker
from locker.model import LockerModel
from locker.types import Command, Operation, State
from locker.mutants import Mutant1_ReserveOccupied, Mutant2_AcceptWrongReservationCode


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
        # Mutant 2 accepts wrong reservation code
        faulty_runner = SequenceRunner(sut_factory=Mutant2_AcceptWrongReservationCode)
        seq = [
            Command(Operation.RESERVE, customer_id="C1"),
            Command(Operation.DEPOSIT, customer_id="C1", code="BAD_CODE"),
        ]
        res = faulty_runner.run(seq, test_id="T_MUTANT2", strategy="Manual")
        self.assertFalse(res.passed)
        self.assertEqual(res.failure_step, 1)
        self.assertIn("Result divergence", res.failure_details)

    def test_run_all_batch(self):
        seqs = [
            [Command(Operation.DISABLE), Command(Operation.ENABLE)],
            [Command(Operation.RESERVE, customer_id="C2"), Command(Operation.CANCEL)],
        ]
        results = self.runner.run_all(seqs, strategy="TestStrategy")
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.passed for r in results))


if __name__ == "__main__":
    unittest.main()
