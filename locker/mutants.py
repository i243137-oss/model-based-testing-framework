from dataclasses import dataclass
from typing import Dict, Type, Any, Optional
from .types import State, Operation, Command, Result, Snapshot
from .sut import ParcelLocker


@dataclass(frozen=True)
class MutantMetadata:
    """Detailed metadata for a system mutant, documenting defect category

    and explicit justification for equivalence or non-equivalence.
    """
    name: str
    description: str
    defect_category: str
    is_equivalent: bool
    equivalence_rationale: str


class Mutant1_ReserveOccupied(ParcelLocker):
    """Mutant 1: Allows reservation when the locker is already OCCUPIED.

    Defect: Fails to reject reservation when the compartment contains a deposited parcel.
    Isolated fault: Specifically permits RESERVE when in OCCUPIED state;
    reservations in MAINTENANCE remain properly rejected.
    """
    def execute(self, command: Command) -> Result:
        if command.operation == Operation.RESERVE:
            # Bug: permits RESERVE in OCCUPIED state as well as AVAILABLE
            if self.state not in (State.AVAILABLE, State.OCCUPIED):
                return Result(False, "locker_not_available")
            self.state = State.RESERVED
            self.customer_id = command.customer_id
            self.reservation_code = f"R-{command.customer_id}"
            return Result(True, "reserved")
        return super().execute(command)


class Mutant2_AcceptWrongReservationCode(ParcelLocker):
    """Mutant 2: Accepts any reservation code during DEPOSIT.

    Defect: Omits code validation against the stored reservation code during parcel deposit.
    """
    def execute(self, command: Command) -> Result:
        if command.operation == Operation.DEPOSIT:
            if self.state != State.RESERVED:
                return Result(False, "not_reserved")
            # Bug: Accepts deposit without validating command.code == self.reservation_code
            self.state = State.OCCUPIED
            self.retrieval_code = f"P-{self.customer_id}"
            return Result(True, "deposited")
        return super().execute(command)


class Mutant3_RetrieveWithoutAuth(ParcelLocker):
    """Mutant 3: Allows retrieval without verifying the retrieval authentication PIN.

    Defect: Bypasses authentication check for parcel pickup.
    """
    def execute(self, command: Command) -> Result:
        if command.operation == Operation.RETRIEVE:
            if self.state != State.OCCUPIED:
                return Result(False, "no_parcel")
            # Bug: Accepts retrieval without validating command.code == self.retrieval_code
            self._clear()
            return Result(True, "retrieved")
        return super().execute(command)


class Mutant4_DoubleRetrieve(ParcelLocker):
    """Mutant 4: Fails to clear locker upon retrieval, allowing duplicate retrieval.

    Defect: State remains OCCUPIED after successful RETRIEVE instead of transitioning to AVAILABLE.
    """
    def execute(self, command: Command) -> Result:
        if command.operation == Operation.RETRIEVE:
            if self.state != State.OCCUPIED:
                return Result(False, "no_parcel")
            if command.code != self.retrieval_code:
                return Result(False, "invalid_retrieval_code")
            # Bug: Omits self._clear(), leaving the compartment OCCUPIED
            return Result(True, "retrieved")
        return super().execute(command)


class Mutant5_ExpireWhenNotExpired(ParcelLocker):
    """Mutant 5: Prematurely expires an active reservation even when expired=False.

    Defect: Ignores the explicit expiration condition guard.
    """
    def execute(self, command: Command) -> Result:
        if command.operation == Operation.EXPIRE:
            if self.state != State.RESERVED:
                return Result(False, "not_reserved")
            # Bug: Does not verify command.expired is True
            self._clear()
            return Result(True, "expired")
        return super().execute(command)


class Mutant6_CancelRetainsCredentials(ParcelLocker):
    """Mutant 6: Resets state to AVAILABLE upon CANCEL but leaks stale credentials.

    Defect: Fails to wipe reservation_code and customer_id on cancellation.
    """
    def execute(self, command: Command) -> Result:
        if command.operation == Operation.CANCEL:
            if self.state != State.RESERVED:
                return Result(False, "not_reserved")
            # Bug: Changes state to AVAILABLE but does not clear credentials
            self.state = State.AVAILABLE
            return Result(True, "cancelled")
        return super().execute(command)


class Mutant7_MaintenanceWhenReserved(ParcelLocker):
    """Mutant 7: Allows placing the locker into MAINTENANCE while RESERVED.

    Defect: Inadequately guards DISABLE, permitting maintenance when an active reservation exists.
    Isolated fault: Specifically permits DISABLE in RESERVED; DISABLE in OCCUPIED remains rejected.
    """
    def execute(self, command: Command) -> Result:
        if command.operation == Operation.DISABLE:
            # Bug: Allows DISABLE when state is RESERVED (in addition to AVAILABLE)
            if self.state not in (State.AVAILABLE, State.RESERVED):
                return Result(False, "cannot_disable")
            self.state = State.MAINTENANCE
            return Result(True, "disabled")
        return super().execute(command)


class Mutant8_EnableWhenNotMaintenance(ParcelLocker):
    """Mutant 8: Allows ENABLE operation when locker is not in MAINTENANCE.

    Defect: Omits the precondition check requiring the locker to be in MAINTENANCE before enabling.
    """
    def execute(self, command: Command) -> Result:
        if command.operation == Operation.ENABLE:
            # Bug: Does not check if self.state == State.MAINTENANCE
            self.state = State.AVAILABLE
            return Result(True, "enabled")
        return super().execute(command)


class Mutant9_DepositDuringMaintenance(ParcelLocker):
    """Mutant 9: Allows DEPOSIT into a compartment that is in MAINTENANCE.

    Defect: Inadequately guards deposit against maintenance state.
    """
    def execute(self, command: Command) -> Result:
        if command.operation == Operation.DEPOSIT:
            if self.state not in (State.RESERVED, State.MAINTENANCE):
                return Result(False, "not_reserved")
            if self.state == State.RESERVED and command.code != self.reservation_code:
                return Result(False, "invalid_reservation_code")
            # Bug: Allows deposit while in MAINTENANCE
            self.state = State.OCCUPIED
            self.retrieval_code = f"P-{self.customer_id}"
            return Result(True, "deposited")
        return super().execute(command)


class Mutant10_MutateOnInvalidDeposit(ParcelLocker):
    """Mutant 10: Mutates retrieval credentials even when deposit was rejected with invalid code.

    Defect: Violates the non-mutation invariant on rejected operations.
    """
    def execute(self, command: Command) -> Result:
        if command.operation == Operation.DEPOSIT:
            if self.state != State.RESERVED:
                return Result(False, "not_reserved")
            if command.code != self.reservation_code:
                # Bug: Mutates internal credential before returning rejection
                self.retrieval_code = "CORRUPTED_CODE"
                return Result(False, "invalid_reservation_code")
            self.state = State.OCCUPIED
            self.retrieval_code = f"P-{self.customer_id}"
            return Result(True, "deposited")
        return super().execute(command)


class EquivalentMutant_RedundantCheck(ParcelLocker):
    """Example Equivalent Mutant: Contains an internal syntactic variation that does not

    alter observable behavior under any input sequence.
    """
    def execute(self, command: Command) -> Result:
        # Syntactic variation: redundant defensive check that evaluates to the same behavior
        if command.operation == Operation.DISABLE and self.state == State.AVAILABLE:
            self.state = State.MAINTENANCE
            return Result(True, "disabled")
        return super().execute(command)


# Registry of the primary 10 evaluation mutants
ALL_MUTANTS: Dict[str, Type[ParcelLocker]] = {
    "Mutant1_ReserveOccupied": Mutant1_ReserveOccupied,
    "Mutant2_AcceptWrongReservationCode": Mutant2_AcceptWrongReservationCode,
    "Mutant3_RetrieveWithoutAuth": Mutant3_RetrieveWithoutAuth,
    "Mutant4_DoubleRetrieve": Mutant4_DoubleRetrieve,
    "Mutant5_ExpireWhenNotExpired": Mutant5_ExpireWhenNotExpired,
    "Mutant6_CancelRetainsCredentials": Mutant6_CancelRetainsCredentials,
    "Mutant7_MaintenanceWhenReserved": Mutant7_MaintenanceWhenReserved,
    "Mutant8_EnableWhenNotMaintenance": Mutant8_EnableWhenNotMaintenance,
    "Mutant9_DepositDuringMaintenance": Mutant9_DepositDuringMaintenance,
    "Mutant10_MutateOnInvalidDeposit": Mutant10_MutateOnInvalidDeposit,
}

# Explicit metadata documenting equivalence status and rationale for every mutant
ALL_MUTANT_METADATA: Dict[str, MutantMetadata] = {
    "Mutant1_ReserveOccupied": MutantMetadata(
        name="Mutant1_ReserveOccupied",
        description="Allows reserving compartment when it is already OCCUPIED.",
        defect_category="Precondition Bypass",
        is_equivalent=False,
        equivalence_rationale=(
            "Non-equivalent: Permits RESERVE when state is OCCUPIED. Observable difference: "
            "SUT returns Result(False, 'locker_not_available') while mutant returns Result(True, 'reserved')."
        ),
    ),
    "Mutant2_AcceptWrongReservationCode": MutantMetadata(
        name="Mutant2_AcceptWrongReservationCode",
        description="Accepts incorrect reservation code during parcel deposit.",
        defect_category="Credential Verification Bypass",
        is_equivalent=False,
        equivalence_rationale=(
            "Non-equivalent: Accepts deposit with invalid code. Observable difference: "
            "SUT returns Result(False, 'invalid_reservation_code') while mutant transitions to OCCUPIED."
        ),
    ),
    "Mutant3_RetrieveWithoutAuth": MutantMetadata(
        name="Mutant3_RetrieveWithoutAuth",
        description="Allows parcel retrieval without valid authentication PIN.",
        defect_category="Authentication Bypass",
        is_equivalent=False,
        equivalence_rationale=(
            "Non-equivalent: Accepts retrieval with invalid PIN. Observable difference: "
            "SUT returns Result(False, 'invalid_retrieval_code') while mutant transitions to AVAILABLE."
        ),
    ),
    "Mutant4_DoubleRetrieve": MutantMetadata(
        name="Mutant4_DoubleRetrieve",
        description="Fails to clear compartment upon retrieval, allowing duplicate retrieval.",
        defect_category="Post-Condition & Cleanup Omission",
        is_equivalent=False,
        equivalence_rationale=(
            "Non-equivalent: Fails to clear locker on retrieval. Observable difference: "
            "Snapshot state remains OCCUPIED instead of AVAILABLE, allowing duplicate retrieval."
        ),
    ),
    "Mutant5_ExpireWhenNotExpired": MutantMetadata(
        name="Mutant5_ExpireWhenNotExpired",
        description="Prematurely expires reservation when explicit expired flag is False.",
        defect_category="Guard Condition Omission",
        is_equivalent=False,
        equivalence_rationale=(
            "Non-equivalent: Prematurely expires when expired=False. Observable difference: "
            "SUT returns Result(False, 'not_expired') while mutant returns Result(True, 'expired')."
        ),
    ),
    "Mutant6_CancelRetainsCredentials": MutantMetadata(
        name="Mutant6_CancelRetainsCredentials",
        description="Fails to clear customer and reservation credentials on cancel.",
        defect_category="State Leak / Invariant Violation",
        is_equivalent=False,
        equivalence_rationale=(
            "Non-equivalent: Retains credentials upon cancel. Observable difference: "
            "Snapshot fields customer_id and reservation_code remain non-None in AVAILABLE state."
        ),
    ),
    "Mutant7_MaintenanceWhenReserved": MutantMetadata(
        name="Mutant7_MaintenanceWhenReserved",
        description="Allows placing compartment into maintenance while reserved.",
        defect_category="Precondition Bypass",
        is_equivalent=False,
        equivalence_rationale=(
            "Non-equivalent: Allows DISABLE when RESERVED. Observable difference: "
            "SUT returns Result(False, 'cannot_disable') while mutant transitions to MAINTENANCE."
        ),
    ),
    "Mutant8_EnableWhenNotMaintenance": MutantMetadata(
        name="Mutant8_EnableWhenNotMaintenance",
        description="Allows enabling locker when it is not in maintenance.",
        defect_category="Precondition Bypass",
        is_equivalent=False,
        equivalence_rationale=(
            "Non-equivalent: Allows ENABLE when in AVAILABLE/RESERVED. Observable difference: "
            "SUT returns Result(False, 'not_in_maintenance') while mutant returns Result(True, 'enabled')."
        ),
    ),
    "Mutant9_DepositDuringMaintenance": MutantMetadata(
        name="Mutant9_DepositDuringMaintenance",
        description="Allows deposit into a compartment under maintenance.",
        defect_category="Precondition Bypass",
        is_equivalent=False,
        equivalence_rationale=(
            "Non-equivalent: Allows deposit while in MAINTENANCE. Observable difference: "
            "SUT returns Result(False, 'not_reserved') while mutant accepts deposit and transitions to OCCUPIED."
        ),
    ),
    "Mutant10_MutateOnInvalidDeposit": MutantMetadata(
        name="Mutant10_MutateOnInvalidDeposit",
        description="Mutates retrieval credential on rejected deposit attempt.",
        defect_category="Side-Effect / Non-Mutation Violation",
        is_equivalent=False,
        equivalence_rationale=(
            "Non-equivalent: Corrupts retrieval_code on rejected deposit. Observable difference: "
            "Violates the non-mutation invariant on rejected operations."
        ),
    ),
    "EquivalentMutant_RedundantCheck": MutantMetadata(
        name="EquivalentMutant_RedundantCheck",
        description="Adds redundant internal check before disabling available locker.",
        defect_category="Syntactic Redundancy",
        is_equivalent=True,
        equivalence_rationale=(
            "Semantically equivalent: Produces identical outputs and state transitions "
            "for all valid and invalid operation sequences."
        ),
    ),
}

MUTANT_DESCRIPTIONS: Dict[str, str] = {
    m_name: meta.description for m_name, meta in ALL_MUTANT_METADATA.items()
}
