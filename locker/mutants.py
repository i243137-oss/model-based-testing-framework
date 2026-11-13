from typing import Dict, Type, Any
from .types import State, Operation, Command, Result, Snapshot
from .sut import ParcelLocker


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


# Registry of all implemented mutants
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

MUTANT_DESCRIPTIONS: Dict[str, str] = {
    "Mutant1_ReserveOccupied": "Allows reserving compartment when it is already OCCUPIED.",
    "Mutant2_AcceptWrongReservationCode": "Accepts incorrect reservation code during parcel deposit.",
    "Mutant3_RetrieveWithoutAuth": "Allows parcel retrieval without valid authentication PIN.",
    "Mutant4_DoubleRetrieve": "Fails to clear compartment upon retrieval, allowing duplicate retrieval.",
    "Mutant5_ExpireWhenNotExpired": "Prematurely expires reservation when explicit expired flag is False.",
    "Mutant6_CancelRetainsCredentials": "Fails to clear customer and reservation credentials on cancel.",
    "Mutant7_MaintenanceWhenReserved": "Allows placing compartment into maintenance while reserved.",
    "Mutant8_EnableWhenNotMaintenance": "Allows enabling locker when it is not in maintenance.",
    "Mutant9_DepositDuringMaintenance": "Allows deposit into a compartment under maintenance.",
    "Mutant10_MutateOnInvalidDeposit": "Mutates retrieval credential on rejected deposit attempt.",
}
