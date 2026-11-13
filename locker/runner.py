import time
from dataclasses import dataclass, field
from typing import List, Optional, Any, Callable, Tuple

from .types import State, Command, Result, Snapshot, Operation
from .sut import ParcelLocker
from .model import LockerModel


@dataclass
class StepRecord:
    step_index: int
    command: Command
    from_state: State
    expected_result: Result
    actual_result: Result
    expected_snapshot: Snapshot
    actual_snapshot: Snapshot
    diverged: bool
    invariant_violation: Optional[str] = None


@dataclass
class TestExecutionResult:
    test_id: str
    strategy: str
    sequence: List[Command]
    initial_state: State
    passed: bool
    expected_final_state: State
    actual_final_state: State
    failure_step: Optional[int] = None
    failure_details: Optional[str] = None
    expected_result: Optional[Result] = None
    actual_result: Optional[Result] = None
    execution_time: float = 0.0
    trace: List[Tuple[State, Command, bool, State]] = field(default_factory=list)
    step_records: List[StepRecord] = field(default_factory=list)


class SequenceRunner:
    """Automated test execution engine and oracle.

    Executes command sequences against both the System Under Test (SUT) and
    the independent executable model. Performs dual-oracle verification:
    1. Operational Result comparison (accepted flag and message).
    2. Complete observable Snapshot comparison (state and credentials).
    3. Structural domain invariant checks after each step.
    4. Non-mutation checks on all rejected operations.
    """

    def __init__(
        self,
        sut_factory: Callable[[], Any] = ParcelLocker,
        model_factory: Callable[[], LockerModel] = LockerModel,
    ):
        self.sut_factory = sut_factory
        self.model_factory = model_factory

    def run(
        self,
        sequence: List[Command],
        test_id: str = "T1",
        strategy: str = "Unknown",
    ) -> TestExecutionResult:
        """Execute a single test sequence against fresh SUT and Model instances."""
        start_time = time.perf_counter()

        sut = self.sut_factory()
        model = self.model_factory()

        initial_state = sut.snapshot().state
        passed = True
        failure_step: Optional[int] = None
        failure_details: Optional[str] = None
        last_exp_res: Optional[Result] = None
        last_act_res: Optional[Result] = None

        trace: List[Tuple[State, Command, bool, State]] = []
        step_records: List[StepRecord] = []

        for idx, cmd in enumerate(sequence):
            sut_before = sut.snapshot()
            model_before = model.snapshot()

            # Execute against SUT and Model
            try:
                act_res: Result = sut.execute(cmd)
            except Exception as e:
                act_res = Result(accepted=False, message=f"EXCEPTION_{type(e).__name__}: {e}")

            exp_res: Result = model.step(cmd)
            sut_after: Snapshot = sut.snapshot()
            model_after: Snapshot = model.snapshot()

            last_exp_res = exp_res
            last_act_res = act_res

            # Record step transition trace based on actual execution on SUT
            trace.append((sut_before.state, cmd, act_res.accepted, sut_after.state))

            diverged = False
            invariant_err: Optional[str] = None

            # 1. Operational Result verification
            if exp_res.accepted != act_res.accepted or exp_res.message != act_res.message:
                diverged = True
                failure_details = (
                    f"Result divergence at step {idx} ({cmd.operation}): "
                    f"expected Result(accepted={exp_res.accepted}, message='{exp_res.message}'), "
                    f"got Result(accepted={act_res.accepted}, message='{act_res.message}')"
                )

            # 2. Complete Snapshot verification
            elif (
                sut_after.state != model_after.state
                or sut_after.customer_id != model_after.customer_id
                or sut_after.reservation_code != model_after.reservation_code
                or sut_after.retrieval_code != model_after.retrieval_code
            ):
                diverged = True
                failure_details = (
                    f"Snapshot divergence at step {idx} ({cmd.operation}): "
                    f"expected {model_after}, got {sut_after}"
                )

            # 3. Domain Invariant verification
            else:
                inv_ok, inv_msg = LockerModel.verify_invariants(sut_after)
                if not inv_ok:
                    diverged = True
                    invariant_err = inv_msg
                    failure_details = f"Invariant violation at step {idx} ({cmd.operation}): {inv_msg}"

                # Non-mutation invariant: rejected operations must not mutate state or credentials
                elif not act_res.accepted:
                    if (
                        sut_after.state != sut_before.state
                        or sut_after.customer_id != sut_before.customer_id
                        or sut_after.reservation_code != sut_before.reservation_code
                        or sut_after.retrieval_code != sut_before.retrieval_code
                    ):
                        diverged = True
                        invariant_err = "Rejected operation mutated SUT state or credentials"
                        failure_details = f"Non-mutation invariant violation at step {idx}: rejected operation changed state"

                # Post-operation cleanup invariant: RETRIEVE, CANCEL, EXPIRE when accepted must clear credentials
                elif act_res.accepted and cmd.operation in (Operation.RETRIEVE, Operation.CANCEL, Operation.EXPIRE):
                    if (
                        sut_after.customer_id is not None
                        or sut_after.reservation_code is not None
                        or sut_after.retrieval_code is not None
                    ):
                        diverged = True
                        invariant_err = f"Successful {cmd.operation} failed to clear customer/credentials"
                        failure_details = f"Cleanup invariant violation at step {idx}: credentials retained after {cmd.operation}"

            step_records.append(
                StepRecord(
                    step_index=idx,
                    command=cmd,
                    from_state=sut_before.state,
                    expected_result=exp_res,
                    actual_result=act_res,
                    expected_snapshot=model_after,
                    actual_snapshot=sut_after,
                    diverged=diverged,
                    invariant_violation=invariant_err,
                )
            )

            if diverged and passed:
                passed = False
                failure_step = idx
                # Stop on first divergence to pinpoint exact defect
                break

        elapsed = time.perf_counter() - start_time
        final_sut_state = sut.snapshot().state
        final_model_state = model.snapshot().state

        return TestExecutionResult(
            test_id=test_id,
            strategy=strategy,
            sequence=sequence,
            initial_state=initial_state,
            passed=passed,
            expected_final_state=final_model_state,
            actual_final_state=final_sut_state,
            failure_step=failure_step,
            failure_details=failure_details,
            expected_result=last_exp_res,
            actual_result=last_act_res,
            execution_time=elapsed,
            trace=trace,
            step_records=step_records,
        )

    def run_all(
        self,
        sequences: List[List[Command]],
        strategy: str = "Unknown",
        id_prefix: str = "TEST",
    ) -> List[TestExecutionResult]:
        """Execute a batch of sequences and return execution results."""
        results: List[TestExecutionResult] = []
        for i, seq in enumerate(sequences):
            test_id = f"{id_prefix}_{strategy}_{i+1:04d}"
            res = self.run(seq, test_id=test_id, strategy=strategy)
            results.append(res)
        return results
