from dataclasses import dataclass, field
from typing import List, Tuple, Set, Dict, Any, Optional

from .types import State, Operation, Command

# Complete set of defined model states
ALL_STATES: Set[State] = {
    State.AVAILABLE,
    State.RESERVED,
    State.OCCUPIED,
    State.MAINTENANCE,
}

# 7 defined primary valid state-transition paths
VALID_STATE_TRANSITIONS: Set[Tuple[State, Operation, State]] = {
    (State.AVAILABLE, Operation.RESERVE, State.RESERVED),
    (State.RESERVED, Operation.DEPOSIT, State.OCCUPIED),
    (State.OCCUPIED, Operation.RETRIEVE, State.AVAILABLE),
    (State.RESERVED, Operation.CANCEL, State.AVAILABLE),
    (State.RESERVED, Operation.EXPIRE, State.AVAILABLE),
    (State.AVAILABLE, Operation.DISABLE, State.MAINTENANCE),
    (State.MAINTENANCE, Operation.ENABLE, State.AVAILABLE),
}

# All 4 states x 8 operations = 32 input state-event combinations
ALL_STATE_OPERATIONS: Set[Tuple[State, Operation]] = {
    (s, op) for s in ALL_STATES for op in Operation
}


@dataclass
class CoverageReport:
    # State coverage
    visited_states: Set[State]
    total_states: int
    state_coverage_pct: float

    # Primary valid transition coverage
    covered_valid_transitions: Set[Tuple[State, Operation, State]]
    total_valid_transitions: int
    valid_transition_coverage_pct: float

    # Comprehensive State-Operation coverage (all 32 state-event combinations)
    covered_state_operations: Set[Tuple[State, Operation]]
    total_state_operations: int
    state_operation_coverage_pct: float

    # Transition-pair coverage (consecutive operation pairs executed)
    covered_transition_pairs: Set[Tuple[Operation, Operation]]
    total_transition_pairs: int
    transition_pair_coverage_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "states_visited": len(self.visited_states),
            "total_states": self.total_states,
            "state_coverage_pct": round(self.state_coverage_pct, 2),
            "valid_transitions_covered": len(self.covered_valid_transitions),
            "total_valid_transitions": self.total_valid_transitions,
            "valid_transition_coverage_pct": round(self.valid_transition_coverage_pct, 2),
            "state_operations_covered": len(self.covered_state_operations),
            "total_state_operations": self.total_state_operations,
            "state_operation_coverage_pct": round(self.state_operation_coverage_pct, 2),
            "transition_pairs_covered": len(self.covered_transition_pairs),
            "total_transition_pairs": self.total_transition_pairs,
            "transition_pair_coverage_pct": round(self.transition_pair_coverage_pct, 2),
        }


def calculate_coverage(executed_traces: List[List[Tuple[State, Command, bool, State]]]) -> CoverageReport:
    """Calculate state, transition, and transition-pair coverage from executed test traces.

    Each trace is a list of tuples: (from_state, command, accepted, to_state).
    Explicit denominators are defined for each metric to guarantee academic transparency:
    - State coverage denominator: 4 states.
    - Valid transition denominator: 7 fundamental lifecycle transitions.
    - State-Operation coverage denominator: 32 (4 states x 8 operations).
    - Transition-pair coverage denominator: 64 possible consecutive operation pairs.
    """
    visited_states: Set[State] = {State.AVAILABLE}  # Initial state is always visited
    covered_valid_transitions: Set[Tuple[State, Operation, State]] = set()
    covered_state_operations: Set[Tuple[State, Operation]] = set()
    covered_transition_pairs: Set[Tuple[Operation, Operation]] = set()

    for trace in executed_traces:
        prev_op: Optional[Operation] = None
        for from_state, cmd, accepted, to_state in trace:
            visited_states.add(from_state)
            visited_states.add(to_state)

            op = cmd.operation
            covered_state_operations.add((from_state, op))

            if accepted:
                trans = (from_state, op, to_state)
                if trans in VALID_STATE_TRANSITIONS:
                    covered_valid_transitions.add(trans)

            if prev_op is not None:
                covered_transition_pairs.add((prev_op, op))
            prev_op = op

    total_states = len(ALL_STATES)
    state_cov_pct = (len(visited_states) / total_states) * 100.0 if total_states else 0.0

    total_valid = len(VALID_STATE_TRANSITIONS)
    valid_cov_pct = (len(covered_valid_transitions) / total_valid) * 100.0 if total_valid else 0.0

    total_state_ops = len(ALL_STATE_OPERATIONS)
    state_ops_pct = (len(covered_state_operations) / total_state_ops) * 100.0 if total_state_ops else 0.0

    total_pairs = len(Operation) * len(Operation)  # 8 x 8 = 64
    pair_cov_pct = (len(covered_transition_pairs) / total_pairs) * 100.0 if total_pairs else 0.0

    return CoverageReport(
        visited_states=visited_states,
        total_states=total_states,
        state_coverage_pct=state_cov_pct,
        covered_valid_transitions=covered_valid_transitions,
        total_valid_transitions=total_valid,
        valid_transition_coverage_pct=valid_cov_pct,
        covered_state_operations=covered_state_operations,
        total_state_operations=total_state_ops,
        state_operation_coverage_pct=state_ops_pct,
        covered_transition_pairs=covered_transition_pairs,
        total_transition_pairs=total_pairs,
        transition_pair_coverage_pct=pair_cov_pct,
    )


@dataclass
class MutationSummary:
    total_mutants: int
    detected_mutants: int
    survived_mutants: int
    equivalent_mutants: int
    mutation_score: float
    mutant_details: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_mutants": self.total_mutants,
            "detected_mutants": self.detected_mutants,
            "survived_mutants": self.survived_mutants,
            "equivalent_mutants": self.equivalent_mutants,
            "mutation_score": round(self.mutation_score, 2),
            "mutant_details": self.mutant_details,
        }


def mutation_summary(mutant_results: Dict[str, Dict[str, Any]]) -> MutationSummary:
    """Compute mutation testing metrics.

    Expects mutant_results mapping mutant_name to a dictionary containing:
    - 'detected': bool
    - 'equivalent': bool (optional, default False)
    - 'first_failing_test': str (optional)
    - 'description': str (optional)

    Mutation Score = (Detected Mutants / Total Non-Equivalent Mutants) * 100.
    """
    total = len(mutant_results)
    detected = 0
    equivalent = 0

    for name, data in mutant_results.items():
        is_equiv = data.get("equivalent", False)
        is_det = data.get("detected", False)
        if is_equiv:
            equivalent += 1
        elif is_det:
            detected += 1

    non_equivalent = total - equivalent
    survived = non_equivalent - detected
    score = (detected / non_equivalent * 100.0) if non_equivalent > 0 else 0.0

    return MutationSummary(
        total_mutants=total,
        detected_mutants=detected,
        survived_mutants=survived,
        equivalent_mutants=equivalent,
        mutation_score=score,
        mutant_details=mutant_results,
    )
