import sys
import unittest
from pathlib import Path


SOURCE_DIR = (Path(__file__).resolve().parents[1] / "examples" / "source"
              / "behavior_packs" / "fe_source")
sys.path.insert(0, str(SOURCE_DIR))
from IndustrialModLibFESourceScripts.fluid_transport import move_fluid


WATER = "minecraft:water"
LAVA = "minecraft:lava"


class Tank:
    def __init__(self, capacity, fluid=None, fill_limit=None, drain_limit=None):
        self.capacity = capacity
        self.state = [fluid]
        self.fill_limit = fill_limit
        self.drain_limit = drain_limit

    def get_fluid(self):
        return self.state[0]

    def fill(self, fluid_id, amount, simulate=False):
        existing = self.get_fluid()
        if existing and existing[0] != fluid_id:
            return 0
        stored = existing[1] if existing else 0
        accepted = min(self.capacity - stored, amount)
        if not simulate and self.fill_limit is not None:
            accepted = min(accepted, self.fill_limit)
        if not simulate and accepted:
            self.state[0] = (fluid_id, stored + accepted)
        return accepted

    def drain(self, fluid_id, amount, simulate=False):
        existing = self.get_fluid()
        if not existing or existing[0] != fluid_id:
            return 0
        taken = min(existing[1], amount)
        if not simulate and self.drain_limit is not None:
            taken = min(taken, self.drain_limit)
        if not simulate and taken:
            left = existing[1] - taken
            self.state[0] = (fluid_id, left) if left else None
        return taken


class FluidTransferTests(unittest.TestCase):
    def test_preview_and_execute_respect_remaining_capacity(self):
        source = Tank(1500, (WATER, 1500))
        target = Tank(1000)
        recovery = Tank(1500)

        self.assertEqual(move_fluid(source, target, recovery, simulate=True), (1000, 0, 0, 0))
        self.assertEqual(source.get_fluid(), (WATER, 1500))
        self.assertIsNone(target.get_fluid())
        self.assertIsNone(recovery.get_fluid())
        self.assertEqual(move_fluid(source, target, recovery), (1000, 1000, 0, 0))
        self.assertEqual(source.get_fluid(), (WATER, 500))
        self.assertEqual(target.get_fluid(), (WATER, 1000))
        self.assertEqual(move_fluid(source, target, recovery), (0, 0, 0, 0))

    def test_partial_acceptance_uses_actual_drain_and_separate_restore_view(self):
        source = Tank(1500, (WATER, 1500), fill_limit=0, drain_limit=800)
        target = Tank(1000, fill_limit=300)
        restore = Tank(1500, fill_limit=200)
        restore.state = source.state
        recovery = Tank(1500)

        self.assertEqual(move_fluid(source, target, recovery, restore=restore),
                         (1000, 300, 200, 300))
        self.assertEqual(source.get_fluid(), (WATER, 900))
        self.assertEqual(target.get_fluid(), (WATER, 300))
        self.assertEqual(recovery.get_fluid(), (WATER, 300))

    def test_rejected_delivery_returns_to_source(self):
        source = Tank(1500, (LAVA, 1500))
        target = Tank(1000, fill_limit=0)
        recovery = Tank(1500)

        self.assertEqual(move_fluid(source, target, recovery), (1000, 0, 1000, 0))
        self.assertEqual(source.get_fluid(), (LAVA, 1500))
        self.assertIsNone(target.get_fluid())
        self.assertIsNone(recovery.get_fluid())

    def test_incompatible_target_or_recovery_does_not_drain_source(self):
        source = Tank(1500, (LAVA, 1500))
        target = Tank(1000, (WATER, 100))
        recovery = Tank(1500, (WATER, 200))

        self.assertEqual(move_fluid(source, target, recovery), (0, 0, 0, 0))
        target = Tank(1000)
        self.assertEqual(move_fluid(source, target, recovery), (1000, 0, 0, 0))
        self.assertEqual(source.get_fluid(), (LAVA, 1500))
        self.assertIsNone(target.get_fluid())
        self.assertEqual(recovery.get_fluid(), (WATER, 200))
