class SequenceRunner:
    """TODO: execute each sequence against a fresh SUT and independent model.

    Compare Result and the complete Snapshot after every command. Record the
    first divergence, command index, expected/actual values, and full sequence.
    """
    def run(self, sequence):
        raise NotImplementedError
