from .types import Snapshot, Result, Command

class LockerModel:
    """TODO: implement an independent model from data/requirements.md."""
    def __init__(self):
        self.reset()

    def reset(self):
        # TODO: initialize model state and credentials
        raise NotImplementedError

    def step(self, command: Command) -> Result:
        # TODO: calculate expected result and update model state
        raise NotImplementedError

    def snapshot(self) -> Snapshot:
        # TODO: return all observable model fields
        raise NotImplementedError
