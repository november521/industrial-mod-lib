import unittest

from test_capabilities import EnergySystem


BLOCK = "example:tank"
KEY = "example:fluid"
POSITION = (1, 2, 3)
WATER = "minecraft:water"
LAVA = "minecraft:lava"


class FluidPortTests(unittest.TestCase):
    def setUp(self):
        self.system = EnergySystem("fe", "energy")
        self.engine = self.system._block_entities
        self.engine.block = {"name": BLOCK, "aux": 0}
        self.engine.data = {}

        def provider(dimension, position, face):
            if face not in ("up", "down"):
                return None
            return self.system.create_block_fluid_port(
                dimension, position, KEY, 1000, (WATER, LAVA),
                can_fill=face == "up", can_drain=face == "down")

        self.system.register_block_capability(BLOCK, "fluid", provider)
        self.inlet = self.port("up")
        self.outlet = self.port("down")

    def port(self, face):
        return self.system.get_block_capability(0, POSITION, face, "fluid")

    def test_injection_simulation_permissions_and_shared_capacity(self):
        self.assertIsNone(self.port("north"))
        self.assertEqual(self.inlet.get_capacity(), 1000)
        self.assertEqual(self.outlet.fill(WATER, 1500, simulate=True), 0)
        self.assertEqual(self.inlet.fill(WATER, 1500, simulate=True), 1000)
        self.assertEqual(self.engine.data, {})

        self.assertEqual(self.inlet.fill(WATER, 1500), 1000)
        self.assertEqual(self.outlet.get_fluid(), (WATER, 1000))
        self.assertEqual(self.inlet.fill(WATER, 50), 0)
        self.assertEqual(self.inlet.drain(WATER, 1), 0)
        self.assertEqual(self.outlet.drain(WATER, 250, simulate=True), 250)
        self.assertEqual(self.engine.data, {KEY: {"fluid_id": WATER, "amount": 1000}})

    def test_incompatible_fluids_and_refill_after_emptying(self):
        self.assertEqual(self.outlet.drain(WATER, 1000), 0)
        self.assertEqual(self.inlet.fill("other:oil", 500), 0)
        self.assertEqual(self.inlet.fill(WATER, 500), 500)
        self.assertEqual(self.inlet.fill(LAVA, 500, simulate=True), 0)
        self.assertEqual(self.inlet.fill(LAVA, 500), 0)
        self.assertEqual(self.outlet.drain(LAVA, 500), 0)
        self.assertEqual(self.outlet.drain(WATER, 800), 500)
        self.assertEqual(self.engine.data, {KEY: {}})
        self.assertIsNone(self.inlet.get_fluid())
        self.assertEqual(self.inlet.fill(LAVA, 500), 500)
        self.assertEqual(self.port("down").get_fluid(), (LAVA, 500))

    def test_failure_detection_invalidates_old_face_instances(self):
        self.inlet.fill(WATER, 500)
        saved = self.engine.data
        self.engine.data = None
        self.assertIsNone(self.port("up"))
        self.assertEqual(self.inlet.fill(WATER, 500), 0)
        self.assertIsNone(self.outlet.get_fluid())
        self.engine.data = saved
        self.assertEqual(self.outlet.drain(WATER, 500), 0)
        self.assertEqual(self.port("down").get_fluid(), (WATER, 500))

        active = self.port("down")
        self.engine.block["aux"] = 1
        self.assertEqual(active.drain(WATER, 500), 0)
        self.assertEqual(self.port("down").get_fluid(), (WATER, 500))

    def test_invalid_ids_and_amounts_are_rejected_without_writes(self):
        for invalid in ("water", "minecraft:", "minecraft:water\n", "Minecraft:water"):
            with self.assertRaises(ValueError):
                self.inlet.fill(invalid, 100)
        with self.assertRaises(TypeError):
            self.inlet.fill(None, 100)
        for invalid in (True, 0.5, "2"):
            with self.assertRaises(TypeError):
                self.inlet.fill(WATER, invalid)
            with self.assertRaises(TypeError):
                self.outlet.drain(WATER, invalid)
        with self.assertRaises(ValueError):
            self.outlet.drain(WATER, -1)
        with self.assertRaises(ValueError):
            self.system.create_block_fluid_port(0, POSITION, KEY, -1)
        self.assertEqual(self.inlet.fill(WATER, 0), 0)
        self.assertEqual(self.engine.data, {})
