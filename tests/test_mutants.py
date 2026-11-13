import unittest
from locker.mutants import ALL_MUTANTS
from locker.runner import SequenceRunner
from locker.types import Command, Operation


class TestMutants(unittest.TestCase):
    def test_all_mutants_are_detectable(self):
        # We craft specific targeted test sequences designed to expose each mutant defect
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


if __name__ == "__main__":
    unittest.main()
