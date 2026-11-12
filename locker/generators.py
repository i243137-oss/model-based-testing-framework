class RandomWalkGenerator:
    """TODO: reproducible random sequences, including invalid operations."""
    def __init__(self, seed: int, max_length: int):
        self.seed, self.max_length = seed, max_length
    def generate(self, count: int):
        raise NotImplementedError

class CoverageGuidedGenerator:
    """TODO: prioritize currently uncovered states/transitions."""
    def __init__(self, seed: int, max_length: int):
        self.seed, self.max_length = seed, max_length
    def generate(self, count: int):
        raise NotImplementedError

class TransitionPairGenerator:
    """TODO: target adjacent transition pairs."""
    def __init__(self, seed: int, max_length: int):
        self.seed, self.max_length = seed, max_length
    def generate(self, count: int):
        raise NotImplementedError
