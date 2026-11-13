import random
from collections import defaultdict
from typing import List, Tuple, Set, Dict, Optional

from .types import State, Operation, Command
from .model import LockerModel
from .metrics import (
    VALID_STATE_TRANSITIONS,
    VALID_TRANSITION_PAIRS,
    Transition,
    TransitionPair,
)

ALL_OPERATIONS = [
    Operation.RESERVE,
    Operation.CANCEL,
    Operation.DEPOSIT,
    Operation.RETRIEVE,
    Operation.EXPIRE,
    Operation.DISABLE,
    Operation.ENABLE,
    Operation.INVALID_ACCESS,
]


def _build_command(
    op: Operation,
    model: LockerModel,
    valid_attempt: bool,
    rng: random.Random,
    customer_id: str = "C1",
) -> Command:
    """Helper to synthesize a Command for a given operation, choosing parameters

    that either attempt a valid transition or deliberately trigger an invalid/rejected condition.
    """
    if op == Operation.RESERVE:
        cust = customer_id if valid_attempt else rng.choice(["C1", "C2", "C3"])
        return Command(operation=Operation.RESERVE, customer_id=cust)

    elif op == Operation.DEPOSIT:
        if valid_attempt and model.reservation_code:
            code = model.reservation_code
        else:
            code = "WRONG_CODE" if rng.random() < 0.7 else f"R-BAD-{rng.randint(10, 99)}"
        return Command(operation=Operation.DEPOSIT, customer_id=customer_id, code=code)

    elif op == Operation.RETRIEVE:
        if valid_attempt and model.retrieval_code:
            code = model.retrieval_code
        else:
            code = "WRONG_CODE" if rng.random() < 0.7 else f"P-BAD-{rng.randint(10, 99)}"
        return Command(operation=Operation.RETRIEVE, customer_id=customer_id, code=code)

    elif op == Operation.EXPIRE:
        expired = True if valid_attempt else False
        return Command(operation=Operation.EXPIRE, customer_id=customer_id, expired=expired)

    elif op == Operation.DISABLE:
        return Command(operation=Operation.DISABLE)

    elif op == Operation.ENABLE:
        return Command(operation=Operation.ENABLE)

    elif op == Operation.CANCEL:
        return Command(operation=Operation.CANCEL, customer_id=customer_id)

    elif op == Operation.INVALID_ACCESS:
        return Command(operation=Operation.INVALID_ACCESS, code="INVALID_KEY")

    return Command(operation=op)


class RandomWalkGenerator:
    """Strategy A: Random Walk Generator.

    Generates test sequences through stochastic walk over the operation space.
    At each step, operations are selected with uniform probability, and parameters
    are randomly toggled between valid credentials and intentionally faulty credentials.
    This exercises both valid paths and negative edge cases.
    """

    def __init__(self, seed: int = 42, max_length: int = 20):
        self.seed = seed
        self.max_length = max(1, max_length)

    def generate(self, count: int) -> List[List[Command]]:
        """Generate `count` independent test sequences with a consistent length budget."""
        rng = random.Random(self.seed)
        sequences: List[List[Command]] = []

        for seq_idx in range(count):
            seq_len = self.max_length
            sim_model = LockerModel()
            seq: List[Command] = []

            for _ in range(seq_len):
                op = rng.choice(ALL_OPERATIONS)
                # 60% chance to attempt valid parameters, 40% chance for invalid/exploratory parameters
                valid_attempt = rng.random() < 0.60
                cust_id = f"C{rng.randint(1, 5)}"
                cmd = _build_command(op, sim_model, valid_attempt, rng, customer_id=cust_id)
                sim_model.step(cmd)
                seq.append(cmd)

            sequences.append(seq)

        return sequences


class CoverageGuidedGenerator:
    """Strategy B: Coverage-Guided Generator.

    Prioritizes unexplored or least-frequently exercised states and transitions.
    Maintains a global execution frequency table across test sequences.
    For each step, evaluates all candidate operations from the current state and
    selects the action that minimizes execution frequency (novelty search / least-covered first).
    """

    def __init__(self, seed: int = 42, max_length: int = 20):
        self.seed = seed
        self.max_length = max(1, max_length)

    def generate(self, count: int) -> List[List[Command]]:
        """Generate `count` independent test sequences prioritizing less-covered states and transitions."""
        rng = random.Random(self.seed)
        sequences: List[List[Command]] = []

        # Global frequency tracking: (source_state, operation, accepted) -> count
        transition_frequencies: Dict[Tuple[State, Operation, bool], int] = defaultdict(int)
        state_frequencies: Dict[State, int] = defaultdict(int)
        state_frequencies[State.AVAILABLE] += 1

        for seq_idx in range(count):
            seq_len = self.max_length
            sim_model = LockerModel()
            seq: List[Command] = []

            for _ in range(seq_len):
                current_state = sim_model.state

                # Generate candidates: both valid and invalid attempts for all operations
                candidates = []
                for op in ALL_OPERATIONS:
                    for valid_attempt in (True, False):
                        # Dry run on a clone of the model to evaluate outcome
                        dry_model = LockerModel()
                        dry_model.state = sim_model.state
                        dry_model.customer_id = sim_model.customer_id
                        dry_model.reservation_code = sim_model.reservation_code
                        dry_model.retrieval_code = sim_model.retrieval_code

                        cust_id = f"C{(seq_idx % 3) + 1}"
                        cmd = _build_command(op, dry_model, valid_attempt, rng, customer_id=cust_id)
                        res = dry_model.step(cmd)
                        next_state = dry_model.state
                        key = (current_state, op, res.accepted)

                        # Score: lower frequency = higher priority.
                        # Heuristic: heavily prioritize unexercised transitions and least-visited target states
                        trans_count = transition_frequencies[key]
                        state_count = state_frequencies[next_state]
                        score = trans_count * 10 + state_count

                        candidates.append((score, cmd, key, next_state))

                # Sort by lowest score, break ties randomly using rng
                rng.shuffle(candidates)
                candidates.sort(key=lambda c: c[0])

                chosen_score, chosen_cmd, chosen_key, chosen_next_state = candidates[0]
                sim_model.step(chosen_cmd)
                seq.append(chosen_cmd)

                # Update global frequencies
                transition_frequencies[chosen_key] += 1
                state_frequencies[chosen_next_state] += 1

            sequences.append(seq)

        return sequences


class TransitionPairGenerator:
    """Strategy C: Transition-Pair Generator.

    Targets valid, connected consecutive transition pairs:
        (t1, t2) where t1.target_state == t2.source_state
    as defined by the state machine (all 13 valid transition pairs).

    The generator tracks globally covered transition pairs and actively steers
    sequences to complete uncovered pairs, chaining transitions while also
    testing negative edge cases.
    """

    def __init__(self, seed: int = 42, max_length: int = 20):
        self.seed = seed
        self.max_length = max(1, max_length)

    def generate(self, count: int) -> List[List[Command]]:
        """Generate `count` independent test sequences targeting state-machine transition pairs."""
        rng = random.Random(self.seed)
        sequences: List[List[Command]] = []

        # Global set of covered connected transition pairs
        covered_pairs: Set[TransitionPair] = set()

        # Pre-index valid outgoing transitions by source state
        transitions_from: Dict[State, List[Transition]] = defaultdict(list)
        for t in VALID_STATE_TRANSITIONS:
            transitions_from[t[0]].append(t)

        for seq_idx in range(count):
            seq_len = self.max_length
            sim_model = LockerModel()
            seq: List[Command] = []
            prev_trans: Optional[Transition] = None

            for _ in range(seq_len):
                current_state = sim_model.state
                available_outgoing = transitions_from.get(current_state, [])

                # Evaluate outgoing transitions that can form an uncovered pair with prev_trans
                candidate_actions = []

                if available_outgoing:
                    for t in available_outgoing:
                        op = t[1]
                        pair = (prev_trans, t) if prev_trans is not None and prev_trans[2] == t[0] else None
                        is_new_pair = pair is not None and pair in VALID_TRANSITION_PAIRS and pair not in covered_pairs

                        # Score for choosing this transition:
                        # - Big bonus if it directly completes an uncovered transition pair
                        # - Bonus if the target state has outgoing transitions with uncovered pairs
                        priority = 0
                        if is_new_pair:
                            priority += 1000

                        # Look ahead: how many uncovered pairs can be formed from target state t[2]?
                        future_uncovered = sum(
                            1 for next_t in transitions_from.get(t[2], [])
                            if (t, next_t) in VALID_TRANSITION_PAIRS and (t, next_t) not in covered_pairs
                        )
                        priority += future_uncovered * 100

                        candidate_actions.append((priority, op, True, t))

                # Also consider invalid operations occasionally (20% chance) to fuzz guards
                # while preserving transition-pair focus
                if not candidate_actions or rng.random() < 0.20:
                    invalid_op = rng.choice(ALL_OPERATIONS)
                    candidate_actions.append((-50, invalid_op, False, None))

                # Shuffle to randomize ties, then sort by highest priority
                rng.shuffle(candidate_actions)
                candidate_actions.sort(key=lambda a: a[0], reverse=True)

                chosen_priority, chosen_op, valid_attempt, next_trans = candidate_actions[0]
                cust_id = f"C{(seq_idx % 4) + 1}"
                cmd = _build_command(chosen_op, sim_model, valid_attempt, rng, customer_id=cust_id)
                res = sim_model.step(cmd)

                if res.accepted and next_trans is not None:
                    curr_trans = (current_state, chosen_op, sim_model.state)
                    if prev_trans is not None and prev_trans[2] == curr_trans[0]:
                        pair = (prev_trans, curr_trans)
                        if pair in VALID_TRANSITION_PAIRS:
                            covered_pairs.add(pair)
                    prev_trans = curr_trans
                else:
                    prev_trans = None

                seq.append(cmd)

            sequences.append(seq)

        return sequences
