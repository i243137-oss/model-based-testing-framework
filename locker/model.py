from .types import State, Operation, Command, Result, Snapshot

class LockerModel:
    """Independent executable state-machine model of the Smart Parcel Locker.

    This model serves as the ground-truth specification (test oracle) for expected
    system behavior, state transitions, credential lifecycles, and state invariants.
    It is implemented independently from any SUT implementation.
    """

    def __init__(self):
        self.state: State = State.AVAILABLE
        self.customer_id: str | None = None
        self.reservation_code: str | None = None
        self.retrieval_code: str | None = None
        self.reset()

    def reset(self) -> None:
        """Reset the model to its initial available state with no credentials."""
        self.state = State.AVAILABLE
        self.customer_id = None
        self.reservation_code = None
        self.retrieval_code = None

    def snapshot(self) -> Snapshot:
        """Return a complete, independent snapshot of the model's observable fields."""
        return Snapshot(
            state=self.state,
            customer_id=self.customer_id,
            reservation_code=self.reservation_code,
            retrieval_code=self.retrieval_code,
        )

    def is_operation_valid(self, command: Command) -> bool:
        """Check whether a command meets all preconditions and guards in the current state."""
        op = command.operation
        if op == Operation.RESERVE:
            return self.state == State.AVAILABLE
        elif op == Operation.CANCEL:
            return self.state == State.RESERVED
        elif op == Operation.DEPOSIT:
            return self.state == State.RESERVED and command.code == self.reservation_code
        elif op == Operation.RETRIEVE:
            return self.state == State.OCCUPIED and command.code == self.retrieval_code
        elif op == Operation.EXPIRE:
            return self.state == State.RESERVED and command.expired is True
        elif op == Operation.DISABLE:
            return self.state == State.AVAILABLE
        elif op == Operation.ENABLE:
            return self.state == State.MAINTENANCE
        elif op == Operation.INVALID_ACCESS:
            return False
        return False

    def step(self, command: Command) -> Result:
        """Calculate expected result, execute state transition, and update credentials.

        If the command is rejected, the state and credentials must not be mutated.
        """
        op = command.operation

        if op == Operation.RESERVE:
            if self.state != State.AVAILABLE:
                return Result(accepted=False, message="locker_not_available")
            self.state = State.RESERVED
            self.customer_id = command.customer_id
            self.reservation_code = f"R-{command.customer_id}"
            return Result(accepted=True, message="reserved")

        elif op == Operation.CANCEL:
            if self.state != State.RESERVED:
                return Result(accepted=False, message="not_reserved")
            self._clear()
            return Result(accepted=True, message="cancelled")

        elif op == Operation.DEPOSIT:
            if self.state != State.RESERVED:
                return Result(accepted=False, message="not_reserved")
            if command.code != self.reservation_code:
                return Result(accepted=False, message="invalid_reservation_code")
            self.state = State.OCCUPIED
            self.retrieval_code = f"P-{self.customer_id}"
            return Result(accepted=True, message="deposited")

        elif op == Operation.RETRIEVE:
            if self.state != State.OCCUPIED:
                return Result(accepted=False, message="no_parcel")
            if command.code != self.retrieval_code:
                return Result(accepted=False, message="invalid_retrieval_code")
            self._clear()
            return Result(accepted=True, message="retrieved")

        elif op == Operation.EXPIRE:
            if self.state != State.RESERVED:
                return Result(accepted=False, message="not_reserved")
            if not command.expired:
                return Result(accepted=False, message="not_expired")
            self._clear()
            return Result(accepted=True, message="expired")

        elif op == Operation.DISABLE:
            if self.state != State.AVAILABLE:
                return Result(accepted=False, message="cannot_disable")
            self.state = State.MAINTENANCE
            return Result(accepted=True, message="disabled")

        elif op == Operation.ENABLE:
            if self.state != State.MAINTENANCE:
                return Result(accepted=False, message="not_in_maintenance")
            self.state = State.AVAILABLE
            return Result(accepted=True, message="enabled")

        elif op == Operation.INVALID_ACCESS:
            # Attempt an operation with invalid credential - rejected without state change
            return Result(accepted=False, message="invalid_access")

        return Result(accepted=False, message="unknown_operation")

    def _clear(self) -> None:
        """Reset internal fields to available baseline."""
        self.state = State.AVAILABLE
        self.customer_id = None
        self.reservation_code = None
        self.retrieval_code = None

    @staticmethod
    def verify_invariants(snapshot: Snapshot) -> tuple[bool, str]:
        """Verify fundamental domain invariants on a given snapshot.

        Returns (True, "ok") if invariant holds, or (False, failure_reason).
        """
        if snapshot.state == State.AVAILABLE:
            if snapshot.customer_id is not None or snapshot.reservation_code is not None or snapshot.retrieval_code is not None:
                return False, "AVAILABLE state must not retain customer or credential information"

        elif snapshot.state == State.RESERVED:
            if snapshot.customer_id is None:
                return False, "RESERVED state must have an associated customer_id"
            if snapshot.reservation_code != f"R-{snapshot.customer_id}":
                return False, f"RESERVED state has incorrect reservation_code '{snapshot.reservation_code}'"
            if snapshot.retrieval_code is not None:
                return False, "RESERVED state must not have a retrieval_code before deposit"

        elif snapshot.state == State.OCCUPIED:
            if snapshot.customer_id is None:
                return False, "OCCUPIED state must have an associated customer_id"
            if snapshot.retrieval_code != f"P-{snapshot.customer_id}":
                return False, f"OCCUPIED state has incorrect retrieval_code '{snapshot.retrieval_code}'"

        elif snapshot.state == State.MAINTENANCE:
            if snapshot.customer_id is not None or snapshot.reservation_code is not None or snapshot.retrieval_code is not None:
                return False, "MAINTENANCE state must not contain active customer or credential information"

        return True, "ok"
