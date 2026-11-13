import unittest
from locker.generators import (
    RandomWalkGenerator,
    CoverageGuidedGenerator,
    TransitionPairGenerator,
)
from locker.types import Command, Operation


class TestGenerators(unittest.TestCase):
    def test_random_walk_reproducibility(self):
        gen1 = RandomWalkGenerator(seed=123, max_length=10)
        seqs1 = gen1.generate(5)

        gen2 = RandomWalkGenerator(seed=123, max_length=10)
        seqs2 = gen2.generate(5)

        self.assertEqual(len(seqs1), 5)
        self.assertEqual(len(seqs2), 5)
        for s1, s2 in zip(seqs1, seqs2):
            self.assertEqual(s1, s2)

    def test_random_walk_different_seeds(self):
        gen1 = RandomWalkGenerator(seed=123, max_length=10)
        gen2 = RandomWalkGenerator(seed=999, max_length=10)
        seqs1 = gen1.generate(3)
        seqs2 = gen2.generate(3)
        self.assertNotEqual(seqs1, seqs2)

    def test_coverage_guided_reproducibility(self):
        gen1 = CoverageGuidedGenerator(seed=456, max_length=12)
        seqs1 = gen1.generate(4)

        gen2 = CoverageGuidedGenerator(seed=456, max_length=12)
        seqs2 = gen2.generate(4)

        self.assertEqual(len(seqs1), 4)
        for s1, s2 in zip(seqs1, seqs2):
            self.assertEqual(s1, s2)

    def test_transition_pair_reproducibility(self):
        gen1 = TransitionPairGenerator(seed=789, max_length=15)
        seqs1 = gen1.generate(4)

        gen2 = TransitionPairGenerator(seed=789, max_length=15)
        seqs2 = gen2.generate(4)

        self.assertEqual(len(seqs1), 4)
        for s1, s2 in zip(seqs1, seqs2):
            self.assertEqual(s1, s2)

    def test_all_generators_produce_valid_commands(self):
        for GenClass in [RandomWalkGenerator, CoverageGuidedGenerator, TransitionPairGenerator]:
            gen = GenClass(seed=42, max_length=8)
            seqs = gen.generate(3)
            self.assertEqual(len(seqs), 3)
            for seq in seqs:
                self.assertGreaterEqual(len(seq), 1)
                self.assertLessEqual(len(seq), 8)
                for cmd in seq:
                    self.assertIsInstance(cmd, Command)
                    self.assertIsInstance(cmd.operation, Operation)


if __name__ == "__main__":
    unittest.main()
