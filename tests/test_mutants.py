import unittest
from locker.mutants import (
    ALL_MUTANTS,
    ALL_MUTANT_METADATA,
    Mutant1_ReserveOccupied,
    EquivalentMutant_RedundantCheck,
)
from locker.runner import SequenceRunner
from locker.metrics import mutation_summary
from locker.types import Command, Operation, State
from locker.sut import ParcelLocker


class TestMutants(unittest.TestCase):
    def test_mutant1_reserve_occupied_isolated_defect(self):
        # Verify Mutant1 rejects reservation when in RESERVED (not allowing all invalid reserves)
        m1 = Mutant1_ReserveOccupied()
        m1.execute(Command(Operation.RESERVE, customer_id="C1"))
        self.assertEqual(m1.snapshot().state, State.RESERVED)
        res = m1.execute(Command(Operation.RESERVE, customer_id="C2"))
        self.assertFalse(res.accepted, "Mutant1 must not allow reservation while in RESERVED state")

        # But Mutant1 FAILS (improperly accepts) when in OCCUPIED state
        m1.execute(Command(Operation.DEPOSIT, customer_id="C1", code="R-C1"))
        self.assertEqual(m1.snapshot().state, State.OCCUPIED)
        buggy_res = m1.execute(Command(Operation.RESERVE, customer_id="C3"))
        self.assertTrue(buggy_res.accepted, "Mutant1 defect: should improperly accept RESERVE in OCCUPIED")

    def test_all_mutants_are_detectable_by_runner(self):
        detecting_sequences = {
            "Mutant1_ReserveOccupied": [
                Command(Operation.RESERVE, customer_id="C1"),
                Command(Operation.DEPOSIT, customer_id="C1", code="R-C1"),
                Command(Operation.RESERVE, customer_id="C2"),  # Bug: reserves while OCCUPIED
            ],
            "Mutant2_AcceptWrongReservationCode": [
                Command(Operation.RESERVE, customer_id="C1"),
                Command(Operation.DEPOSIT, customer_id="C1", code="WRONG_CODE"),  # Bug: accepts bad code
            ],
            "Mutant3_RetrieveWithoutAuth": [
                Command(Operation.RESERVE, customer_id="C1"),
                Command(Operation.DEPOSIT, customer_id="C1", code="R-C1"),
                Command(Operation.RETRIEVE, customer_id="C1", code="WRONG_PIN"),  # Bug: retrieves without auth
            ],
            "Mutant4_DoubleRetrieve": [
                Command(Operation.RESERVE, customer_id="C1"),
                Command(Operation.DEPOSIT, customer_id="C1", code="R-C1"),
                Command(Operation.RETRIEVE, customer_id="C1", code="P-C1"),
                Command(Operation.RETRIEVE, customer_id="C1", code="P-C1"),  # Bug: double retrieval succeeds
            ],
            "Mutant5_ExpireWhenNotExpired": [
                Command(Operation.RESERVE, customer_id="C1"),
                Command(Operation.EXPIRE, expired=False),  # Bug: expires even though expired=False
            ],
            "Mutant6_CancelRetainsCredentials": [
                Command(Operation.RESERVE, customer_id="C1"),
                Command(Operation.CANCEL),  # Bug: snapshot retains credentials in AVAILABLE state
            ],
            "Mutant7_MaintenanceWhenReserved": [
                Command(Operation.RESERVE, customer_id="C1"),
                Command(Operation.DISABLE),  # Bug: disables while RESERVED
            ],
            "Mutant8_EnableWhenNotMaintenance": [
                Command(Operation.ENABLE),  # Bug: enables while in AVAILABLE
            ],
            "Mutant9_DepositDuringMaintenance": [
                Command(Operation.DISABLE),
                Command(Operation.DEPOSIT, customer_id="C1", code="R-C1"),  # Bug: deposits during MAINTENANCE
            ],
            "Mutant10_MutateOnInvalidDeposit": [
                Command(Operation.RESERVE, customer_id="C1"),
                Command(Operation.DEPOSIT, customer_id="C1", code="WRONG_CODE"),  # Bug: mutates retrieval code
            ],
        }

        self.assertGreaterEqual(len(ALL_MUTANTS), 8)
        for mutant_name, mutant_cls in ALL_MUTANTS.items():
            self.assertIn(mutant_name, detecting_sequences)
            runner = SequenceRunner(sut_factory=mutant_cls)
            seq = detecting_sequences[mutant_name]
            result = runner.run(seq, test_id=f"TEST_{mutant_name}")
            self.assertFalse(
                result.passed,
                f"Mutant '{mutant_name}' should have failed test sequence but passed!",
            )

    def test_mutant_metadata_and_equivalence_documentation(self):
        """Verify that every mutant has structured metadata, defect category,

        and documented non-equivalence rationale.
        """
        self.assertGreaterEqual(len(ALL_MUTANT_METADATA), 10)
        for m_name in ALL_MUTANTS.keys():
            self.assertIn(m_name, ALL_MUTANT_METADATA)
            meta = ALL_MUTANT_METADATA[m_name]
            self.assertEqual(meta.name, m_name)
            self.assertFalse(meta.is_equivalent, f"{m_name} should be documented as non-equivalent")
            self.assertGreater(len(meta.equivalence_rationale), 10)
            self.assertGreater(len(meta.defect_category), 0)

    def test_equivalent_mutant_handling(self):
        """Verify that equivalent mutants are recognized and excluded from mutation score denominator."""
        meta_equiv = ALL_MUTANT_METADATA.get("EquivalentMutant_RedundantCheck")
        self.assertIsNotNone(meta_equiv)
        self.assertTrue(meta_equiv.is_equivalent)

        # Execute equivalent mutant with sample commands: should match reference SUT
        equiv_sut = EquivalentMutant_RedundantCheck()
        ref_sut = ParcelLocker()
        cmd = Command(Operation.DISABLE)
        self.assertEqual(equiv_sut.execute(cmd), ref_sut.execute(cmd))

        # Check mutation metric calculation: equivalent mutants must be excluded from denominator
        mock_results = {
            "m1": {"detected": True, "equivalent": False},
            "m2": {"detected": False, "equivalent": False},
            "equiv1": {"detected": False, "equivalent": True},
        }
        summary = mutation_summary(mock_results)
        self.assertEqual(summary.total_mutants, 3)
        self.assertEqual(summary.equivalent_mutants, 1)
        self.assertEqual(summary.detected_mutants, 1)
        self.assertEqual(summary.survived_mutants, 1)
        # Score = 1 / (3 - 1) * 100 = 50.0%
        self.assertEqual(summary.mutation_score, 50.0)


if __name__ == "__main__":
    unittest.main()
