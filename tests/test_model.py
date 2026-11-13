import unittest
from locker.model import LockerModel
from locker.types import State, Operation, Command, Result, Snapshot


class TestLockerModel(unittest.TestCase):
    def setUp(self):
        self.model = LockerModel()

    def test_initial_state(self):
        snap = self.model.snapshot()
        self.assertEqual(snap.state, State.AVAILABLE)
        self.assertIsNone(snap.customer_id)
        self.assertIsNone(snap.reservation_code)
        self.assertIsNone(snap.retrieval_code)
        ok, _ = LockerModel.verify_invariants(snap)
        self.assertTrue(ok)

    def test_reserve_and_deposit_and_retrieve_lifecycle(self):
        # 1. RESERVE (Rule 1, Rule 2)
        res = self.model.step(Command(Operation.RESERVE, customer_id="C10"))
        self.assertTrue(res.accepted)
        self.assertEqual(res.message, "reserved")
        snap = self.model.snapshot()
        self.assertEqual(snap.state, State.RESERVED)
        self.assertEqual(snap.customer_id, "C10")
        self.assertEqual(snap.reservation_code, "R-C10")
        self.assertIsNone(snap.retrieval_code)
        ok, _ = LockerModel.verify_invariants(snap)
        self.assertTrue(ok)

        # 2. DEPOSIT (Rule 4, Rule 5)
        res = self.model.step(Command(Operation.DEPOSIT, customer_id="C10", code="R-C10"))
        self.assertTrue(res.accepted)
        self.assertEqual(res.message, "deposited")
        snap = self.model.snapshot()
        self.assertEqual(snap.state, State.OCCUPIED)
        self.assertEqual(snap.retrieval_code, "P-C10")
        ok, _ = LockerModel.verify_invariants(snap)
        self.assertTrue(ok)

        # 3. RETRIEVE (Rule 6, Rule 7)
        res = self.model.step(Command(Operation.RETRIEVE, customer_id="C10", code="P-C10"))
        self.assertTrue(res.accepted)
        self.assertEqual(res.message, "retrieved")
        snap = self.model.snapshot()
        self.assertEqual(snap.state, State.AVAILABLE)
        self.assertIsNone(snap.customer_id)
        self.assertIsNone(snap.reservation_code)
        self.assertIsNone(snap.retrieval_code)
        ok, _ = LockerModel.verify_invariants(snap)
        self.assertTrue(ok)

    def test_cancel_lifecycle(self):
        # Rule 3: Cancel accepted only in RESERVED; returns to AVAILABLE
        self.model.step(Command(Operation.RESERVE, customer_id="C5"))
        res = self.model.step(Command(Operation.CANCEL, customer_id="C5"))
        self.assertTrue(res.accepted)
        self.assertEqual(res.message, "cancelled")
        snap = self.model.snapshot()
        self.assertEqual(snap.state, State.AVAILABLE)
        self.assertIsNone(snap.customer_id)
        self.assertIsNone(snap.reservation_code)

    def test_expire_lifecycle(self):
        # Rule 8: Expire accepted only in RESERVED when expired=True
        self.model.step(Command(Operation.RESERVE, customer_id="C8"))
        # Expire with expired=False should fail
        res = self.model.step(Command(Operation.EXPIRE, expired=False))
        self.assertFalse(res.accepted)
        self.assertEqual(res.message, "not_expired")
        self.assertEqual(self.model.state, State.RESERVED)

        # Expire with expired=True should succeed
        res = self.model.step(Command(Operation.EXPIRE, expired=True))
        self.assertTrue(res.accepted)
        self.assertEqual(res.message, "expired")
        self.assertEqual(self.model.state, State.AVAILABLE)
        self.assertIsNone(self.model.customer_id)
        self.assertIsNone(self.model.reservation_code)

    def test_maintenance_lifecycle(self):
        # Rule 9: Disable accepted only in AVAILABLE -> MAINTENANCE
        res = self.model.step(Command(Operation.DISABLE))
        self.assertTrue(res.accepted)
        self.assertEqual(self.model.state, State.MAINTENANCE)

        # Cannot reserve while in maintenance
        res = self.model.step(Command(Operation.RESERVE, customer_id="C1"))
        self.assertFalse(res.accepted)

        # Rule 10: Enable accepted only in MAINTENANCE -> AVAILABLE
        res = self.model.step(Command(Operation.ENABLE))
        self.assertTrue(res.accepted)
        self.assertEqual(self.model.state, State.AVAILABLE)

    def test_all_invalid_state_rejections_and_non_mutation(self):
        """Rule 11 & Rule 12: Verify all invalid operations across all states are rejected

        without modifying system state or credentials.
        """
        # In AVAILABLE: CANCEL, DEPOSIT, RETRIEVE, ENABLE, EXPIRE must be rejected
        for op in [Operation.CANCEL, Operation.DEPOSIT, Operation.RETRIEVE, Operation.ENABLE, Operation.EXPIRE, Operation.INVALID_ACCESS]:
            snap_before = self.model.snapshot()
            res = self.model.step(Command(op, code="XYZ", expired=True))
            self.assertFalse(res.accepted, f"Operation {op} should be rejected in AVAILABLE")
            self.assertEqual(self.model.snapshot(), snap_before)

        # Move to RESERVED: RESERVE, RETRIEVE, DISABLE, ENABLE must be rejected
        self.model.step(Command(Operation.RESERVE, customer_id="C1"))
        self.assertEqual(self.model.state, State.RESERVED)
        snap_res = self.model.snapshot()
        for op in [Operation.RESERVE, Operation.RETRIEVE, Operation.DISABLE, Operation.ENABLE, Operation.INVALID_ACCESS]:
            res = self.model.step(Command(op, code="XYZ"))
            self.assertFalse(res.accepted, f"Operation {op} should be rejected in RESERVED")
            self.assertEqual(self.model.snapshot(), snap_res)

        # Move to OCCUPIED: RESERVE, DEPOSIT, CANCEL, EXPIRE, DISABLE, ENABLE must be rejected
        self.model.step(Command(Operation.DEPOSIT, code="R-C1"))
        self.assertEqual(self.model.state, State.OCCUPIED)
        snap_occ = self.model.snapshot()
        for op in [Operation.RESERVE, Operation.DEPOSIT, Operation.CANCEL, Operation.EXPIRE, Operation.DISABLE, Operation.ENABLE, Operation.INVALID_ACCESS]:
            res = self.model.step(Command(op, code="XYZ", expired=True))
            self.assertFalse(res.accepted, f"Operation {op} should be rejected in OCCUPIED")
            self.assertEqual(self.model.snapshot(), snap_occ)

        # Clear back to AVAILABLE then move to MAINTENANCE
        self.model.step(Command(Operation.RETRIEVE, code="P-C1"))
        self.model.step(Command(Operation.DISABLE))
        self.assertEqual(self.model.state, State.MAINTENANCE)
        snap_maint = self.model.snapshot()
        for op in [Operation.RESERVE, Operation.DEPOSIT, Operation.RETRIEVE, Operation.CANCEL, Operation.EXPIRE, Operation.DISABLE, Operation.INVALID_ACCESS]:
            res = self.model.step(Command(op, code="XYZ", expired=True))
            self.assertFalse(res.accepted, f"Operation {op} should be rejected in MAINTENANCE")
            self.assertEqual(self.model.snapshot(), snap_maint)

    def test_invalid_credential_rejected_without_mutation(self):
        self.model.step(Command(Operation.RESERVE, customer_id="C2"))
        before = self.model.snapshot()

        # Wrong reservation code
        res = self.model.step(Command(Operation.DEPOSIT, code="WRONG_CODE"))
        self.assertFalse(res.accepted)
        self.assertEqual(res.message, "invalid_reservation_code")
        self.assertEqual(self.model.snapshot(), before)

        # Invalid access
        res = self.model.step(Command(Operation.INVALID_ACCESS, code="BAD"))
        self.assertFalse(res.accepted)
        self.assertEqual(res.message, "invalid_access")
        self.assertEqual(self.model.snapshot(), before)

    def test_invariant_verification(self):
        # Corrupt snapshot: AVAILABLE with leftover customer_id
        corrupted = Snapshot(State.AVAILABLE, "C1", None, None)
        ok, msg = LockerModel.verify_invariants(corrupted)
        self.assertFalse(ok)
        self.assertIn("AVAILABLE state must not retain customer", msg)

        # Corrupt snapshot: RESERVED with wrong reservation code format
        corrupted_res = Snapshot(State.RESERVED, "C1", "WRONG_CODE", None)
        ok, msg = LockerModel.verify_invariants(corrupted_res)
        self.assertFalse(ok)
        self.assertIn("incorrect reservation_code", msg)


if __name__ == "__main__":
    unittest.main()
