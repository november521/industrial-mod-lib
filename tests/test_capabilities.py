import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "behavior_packs" / "industrial_mod_lib"))

api = types.ModuleType("mod.server.extraServerApi")
api.GetServerSystemCls = lambda: ServerSystem


class ServerSystem:
    def __init__(self, namespace, name):
        pass


class Engine:
    def CreateBlockInfo(self, level):
        return self

    def CreateBlockEntityData(self, level):
        return self

    def GetBlockNew(self, position, dimension):
        return self.block

    def GetBlockEntityData(self, dimension, position):
        return self.data


api.GetEngineCompFactory = Engine
api.GetLevelId = lambda: "level"
with patch.dict(sys.modules, {
    "mod": types.ModuleType("mod"),
    "mod.server": types.ModuleType("mod.server"),
    api.__name__: api,
}):
    from IndustrialModLibScripts.server import EnergySystem


class CapabilityTests(unittest.TestCase):
    def test_item_provider_resolves_shared_persistent_slots(self):
        system = EnergySystem("fe", "energy")
        system._block_info.block = {"name": "example:machine", "aux": 0}
        system._block_entities.data = {}
        position = (1, 2, 3)

        def provider(dimension, pos, face):
            return system.create_block_item_port(
                dimension, pos, "example:inventory", {0: 64},
                lambda stack: 64, (0,) if face == "up" else (),
                (0,) if face == "down" else ())

        system.register_block_capability("example:machine", "item", provider)
        top = system.get_block_capability(0, position, "up", "item")
        bottom = system.get_block_capability(0, position, "down", "item")
        stack = {"newItemName": "minecraft:apple", "count": 2}
        self.assertIsNone(top.insert(0, stack))
        self.assertEqual(bottom.get_stack(0), stack)
        self.assertEqual(top.get_slot_key(0), bottom.get_slot_key(0))
        self.assertEqual(system._block_entities.data, {"example:inventory:0": stack})
        system._block_info.block["aux"] = 1
        self.assertEqual(top.insert(0, stack), stack)
        self.assertIsNone(bottom.extract(0, 1))
        new_bottom = system.get_block_capability(0, position, "down", "item")
        self.assertEqual(new_bottom.extract(0, 2), stack)
        self.assertEqual(system._block_entities.data["example:inventory:0"], {})
        system._block_entities.data = None
        self.assertIsNone(new_bottom.extract(0, 1))
        self.assertIsNone(system.get_block_capability(0, position, "up", "item"))

    def test_legacy_energy_and_new_capabilities_share_lookup(self):
        system = EnergySystem("fe", "energy")
        system._block_info.block = {"name": "example:machine"}
        energy = system.create_storage(100, 25, 10)
        args = (0, (1, 2, 3), "up")
        system.register_block("example:machine", lambda *args: energy)
        system.register_block_capability("example:machine", "item", lambda *p: p)
        self.assertIs(system.get_block_energy(*args), energy)
        self.assertIs(system.get_block_capability(*args, "energy"), energy)
        self.assertEqual(system.get_block_capability(*args, "item"), args)
        self.assertEqual(energy.receive_energy(50, True), 25)
        self.assertEqual(energy.get_energy_stored(), 0)
        self.assertEqual(energy.receive_energy(50), 25)
        with self.assertRaises(ValueError):
            system.register_block_capability("example:machine", "energy", lambda *p: p)
        with self.assertRaises(ValueError):
            system.get_block_energy(0, (1, 2, 3), "invalid")
        self.assertIsNone(system.get_block_capability(*args, "fluid"))
        system._block_info.block = None
        self.assertIsNone(system.get_block_energy(*args))
