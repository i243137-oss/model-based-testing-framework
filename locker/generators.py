import random
from collections import defaultdict
from typing import List, Tuple, Set, Dict

from .types import State, Operation, Command
from .model import LockerModel

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
        """Generate `count` independent test sequences of length up to `max_length`."""
        rng = random.Random(self.seed)
        sequences: List[List[Command]] = []

        for seq_idx in range(count):
            # Select random sequence length between 1 and max_length
            seq_len = rng.randint(1, self.max_length)
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
        rng = random.Random(self.seed)
        sequences: List[List[Command]] = []

        # Global frequency tracking: (source_state, operation, accepted) -> count
        transition_frequencies: Dict[Tuple[State, Operation, bool], int] = defaultdict(int)
        state_frequencies: Dict[State, int] = defaultdict(int)
        state_frequencies[State.AVAILABLE] += 1

        for seq_idx in range(count):
            seq_len = rng.randint(max(1, self.max_length // 2), self.max_length)
            sim_model = LockerModel()
            seq: List[Command] = []

            for _ in range(seq_len):
                current_state = sim_model.state

                # Generate candidates: both valid and invalid attempts for all operations
                candidates = []
                for op in ALL_OPERATIONS:
                    for valid_attempt in (True, False):
                        # Dry run on a copy of the model to predict outcome
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
                        # Heavy bonus for completely unvisited transitions (freq == 0)
                        # and transitions leading to less-visited states.
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

    Targets pairs of consecutive transitions (t1, t2).
    A transition pair consists of an incoming transition into an intermediate state s_mid,
    followed by an outgoing transition from s_mid.
    The generator maintains a global set of covered transition pairs and actively
    navigates the state machine to trigger uncovered pairs within each sequence.
    """

    def __init__(self, seed: int = 42, max_length: int = 20):
        self.seed = seed
        self.max_length = max(1, max_length)

    def _get_target_pairs(self) -> Set[Tuple[Operation, Operation]]:
        """Define target consecutive operation pairs relevant to the locker lifecycle."""
        # Operational sequences of interest:
        # e.g., (RESERVE, DEPOSIT), (RESERVE, CANCEL), (RESERVE, EXPIRE), (DEPOSIT, RETRIEVE),
        # (DISABLE, ENABLE), (RESERVE, INVALID_ACCESS), (DEPOSIT, INVALID_ACCESS),
        # (RESERVE, RESERVE), (RETRIEVE, RETRIEVE), (ENABLE, DISABLE), etc.
        pairs = set()
        for op1 in ALL_OPERATIONS:
            for op2 in ALL_OPERATIONS:
                pairs.add((op1, op2))
        return pairs

    def generate(self, count: int) -> List[List[Command]]:
        rng = random.Random(self.seed)
        sequences: List[List[Command]] = []

        # Track global pair coverage: (op1, op2)
        covered_pairs: Set[Tuple[Operation, Operation]] = set()
        all_possible_pairs = list(self._get_target_pairs())
        rng.shuffle(all_possible_pairs)

        for seq_idx in range(count):
            seq_len = rng.randint(max(1, self.max_length // 2), self.max_length)
            sim_model = LockerModel()
            seq: List[Command] = []
            prev_op: Operation | None = None

            for _ in range(seq_len):
                current_state = sim_model.state

                # Find candidate operations that form an uncovered pair with prev_op
                candidates = []
                for op in ALL_OPERATIONS:
                    for valid_attempt in (True, False):
                        dry_model = LockerModel()
                        dry_model.state = sim_model.state
                        dry_model.customer_id = sim_model.customer_id
                        dry_model.reservation_code = sim_model.reservation_code
                        dry_model.retrieval_code = sim_model.retrieval_code

                        cust_id = f"C{(seq_idx % 4) + 1}"
                        cmd = _build_command(op, dry_model, valid_attempt, rng, customer_id=cust_id)
                        res = dry_model.step(cmd)

                        pair = (prev_op, op) if prev_op is not None else None
                        is_new_pair = pair is not None and pair not in covered_pairs

                        # Priority:
                        # 1. New uncovered pair with prev_op
                        # 2. Valid transition that moves state forward towards unexplored pairs
                        # 3. Novel operations
                        score = 0
                        if is_new_pair:
                            score -= 100
                        if res.accepted:
                            score -= 10

                        candidates.append((score, cmd, op))

                rng.shuffle(candidates)
                candidates.sort(key=lambda c: c[0])

                chosen_score, chosen_cmd, chosen_op = candidates[0]
                sim_model.step(chosen_cmd)
                seq.append(chosen_cmd)

                if prev_op is not None:
                    covered_pairs.add((prev_op, chosen_op))
                prev_op = chosen_op

            sequences.append(seq)

        return sequences
