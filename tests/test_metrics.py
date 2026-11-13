import unittest
from locker.metrics import calculate_coverage, mutation_summary
from locker.types import State, Operation, Command


class TestMetrics(unittest.TestCase):
    def test_calculate_coverage_lifecycle(self):
        # Full lifecycle trace
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

        # Transition pairs checked
        self.assertGreater(len(report.covered_transition_pairs), 0)

        # Dictionary export
        d = report.to_dict()
        self.assertEqual(d["states_visited"], 4)
        self.assertEqual(d["state_coverage_pct"], 100.0)

    def test_mutation_summary(self):
        mutant_results = {
            "m1": {"detected": True, "equivalent": False},
            "m2": {"detected": True, "equivalent": False},
            "m3": {"detected": False, "equivalent": False},
            "m4": {"detected": False, "equivalent": True},  # Equivalent
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
