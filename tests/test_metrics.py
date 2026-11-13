import unittest
from locker.metrics import (
    calculate_coverage,
    mutation_summary,
    is_valid_transition,
    is_valid_transition_pair,
    get_all_valid_transition_pairs,
    VALID_STATE_TRANSITIONS,
    VALID_TRANSITION_PAIRS,
)
from locker.types import State, Operation, Command


class TestMetrics(unittest.TestCase):
    def test_valid_transitions_and_connected_pairs(self):
        # 7 valid primary transitions
        self.assertEqual(len(VALID_STATE_TRANSITIONS), 7)
        for t in VALID_STATE_TRANSITIONS:
            self.assertTrue(is_valid_transition(t))

        # Dynamic derivation of connected transition pairs
        all_pairs = get_all_valid_transition_pairs()
        self.assertEqual(len(all_pairs), 13)
        self.assertEqual(VALID_TRANSITION_PAIRS, all_pairs)

        # Every valid pair must have t1.target_state == t2.source_state
        for t1, t2 in all_pairs:
            self.assertTrue(is_valid_transition_pair(t1, t2))
            self.assertEqual(t1[2], t2[0])

    def test_disconnected_and_invalid_transition_pairs_rejected(self):
        # Disconnected pair: AVAILABLE->DISABLE->MAINTENANCE followed by AVAILABLE->RESERVE->RESERVED
        # (t1.target is MAINTENANCE, t2.source is AVAILABLE -> mismatch)
        t1 = (State.AVAILABLE, Operation.DISABLE, State.MAINTENANCE)
        t2 = (State.AVAILABLE, Operation.RESERVE, State.RESERVED)
        self.assertFalse(is_valid_transition_pair(t1, t2))

        # Impossible/invalid transition: MAINTENANCE->RETRIEVE->AVAILABLE
        t_invalid = (State.MAINTENANCE, Operation.RETRIEVE, State.AVAILABLE)
        self.assertFalse(is_valid_transition(t_invalid))
        self.assertFalse(is_valid_transition_pair(t1, t_invalid))

    def test_calculate_coverage_lifecycle(self):
        # Trace exercising:
        # 1. AVAILABLE -> RESERVE -> RESERVED (t1)
        # 2. RESERVED -> DEPOSIT -> OCCUPIED (t2)  --> Pair 1: (t1, t2)
        # 3. OCCUPIED -> RETRIEVE -> AVAILABLE (t3) --> Pair 2: (t2, t3)
        # 4. AVAILABLE -> DISABLE -> MAINTENANCE (t4) --> Pair 3: (t3, t4)
        # 5. MAINTENANCE -> ENABLE -> AVAILABLE (t5) --> Pair 4: (t4, t5)
        trace = [
            (State.AVAILABLE, Command(Operation.RESERVE, customer_id="C1"), True, State.RESERVED),
            (State.RESERVED, Command(Operation.DEPOSIT, code="R-C1"), True, State.OCCUPIED),
            (State.OCCUPIED, Command(Operation.RETRIEVE, code="P-C1"), True, State.AVAILABLE),
            (State.AVAILABLE, Command(Operation.DISABLE), True, State.MAINTENANCE),
            (State.MAINTENANCE, Command(Operation.ENABLE), True, State.AVAILABLE),
        ]
        report = calculate_coverage([trace])

        # All 4 states visited
        self.assertEqual(report.state_coverage_pct, 100.0)
        self.assertEqual(len(report.visited_states), 4)

        # 5 of 7 valid transitions covered
        self.assertEqual(len(report.covered_valid_transitions), 5)
        self.assertAlmostEqual(report.valid_transition_coverage_pct, (5 / 7) * 100.0, places=2)

        # 4 connected transition pairs covered out of 13
        self.assertEqual(len(report.covered_transition_pairs), 4)
        self.assertEqual(report.total_transition_pairs, 13)
        self.assertAlmostEqual(report.transition_pair_coverage_pct, (4 / 13) * 100.0, places=2)

        # Ensure dictionary serialization
        d = report.to_dict()
        self.assertEqual(d["transition_pairs_covered"], 4)
        self.assertEqual(d["total_transition_pairs"], 13)

    def test_invalid_operations_break_transition_pair_chain(self):
        # t1 is valid: AVAILABLE -> RESERVE -> RESERVED
        # Step 2: Invalid access (rejected). Must not form a transition pair.
        # Step 3: RESERVED -> DEPOSIT -> OCCUPIED.
        # Since step 2 failed, the chain between t1 and DEPOSIT is broken.
        trace = [
            (State.AVAILABLE, Command(Operation.RESERVE, customer_id="C1"), True, State.RESERVED),
            (State.RESERVED, Command(Operation.INVALID_ACCESS), False, State.RESERVED),
            (State.RESERVED, Command(Operation.DEPOSIT, code="R-C1"), True, State.OCCUPIED),
        ]
        report = calculate_coverage([trace])
        # Neither pair was formed consecutively without interruption
        self.assertEqual(len(report.covered_transition_pairs), 0)

    def test_sequence_boundary_resets_pair_chain(self):
        # Sequence 1 ends at RESERVED (via RESERVE)
        seq1 = [
            (State.AVAILABLE, Command(Operation.RESERVE, customer_id="C1"), True, State.RESERVED),
        ]
        # Sequence 2 starts fresh at AVAILABLE
        seq2 = [
            (State.AVAILABLE, Command(Operation.DISABLE), True, State.MAINTENANCE),
        ]
        report = calculate_coverage([seq1, seq2])
        # Across sequence boundary, no pair should be formed
        self.assertEqual(len(report.covered_transition_pairs), 0)

    def test_repeated_pairs_do_not_inflate_coverage(self):
        # Repeating the same pair twice must not count as 2 distinct pairs
        trace1 = [
            (State.AVAILABLE, Command(Operation.RESERVE, customer_id="C1"), True, State.RESERVED),
            (State.RESERVED, Command(Operation.CANCEL), True, State.AVAILABLE),
        ]
        trace2 = [
            (State.AVAILABLE, Command(Operation.RESERVE, customer_id="C2"), True, State.RESERVED),
            (State.RESERVED, Command(Operation.CANCEL), True, State.AVAILABLE),
        ]
        report = calculate_coverage([trace1, trace2])
        self.assertEqual(len(report.covered_transition_pairs), 1)

    def test_mutation_summary(self):
        mutant_results = {
            "m1": {"detected": True, "equivalent": False},
            "m2": {"detected": True, "equivalent": False},
            "m3": {"detected": False, "equivalent": False},
            "m4": {"detected": False, "equivalent": True},  # Equivalent mutant excluded from denominator
        }
        summary = mutation_summary(mutant_results)
        self.assertEqual(summary.total_mutants, 4)
        self.assertEqual(summary.detected_mutants, 2)
        self.assertEqual(summary.survived_mutants, 1)
        self.assertEqual(summary.equivalent_mutants, 1)
        # Score = 2 / (4 - 1) * 100 = 66.67%
        self.assertAlmostEqual(summary.mutation_score, 66.67, places=2)


if __name__ == "__main__":
    unittest.main()
