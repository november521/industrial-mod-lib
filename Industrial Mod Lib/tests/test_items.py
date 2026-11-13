import unittest

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "behavior_packs" / "industrial_mod_lib"))
from IndustrialModLibScripts.items import ItemPort


class ItemPortTests(unittest.TestCase):
    def setUp(self):
        self.data = {}
        self.stack = {"newItemName": "minecraft:apple", "count": 12,
                      "userData": {"label": ["a"]}}
        self.input = self.port((0,), ())
        self.output = self.port((), (0,))

    def port(self, insert, extract):
        return ItemPort(lambda: self.data, (0, (1, 2, 3), "items"),
                        {0: 10}, lambda stack: 8, insert, extract)

    def test_simulation_and_partial_transfer(self):
        self.assertEqual(self.input.insert(0, self.stack, True)["count"], 4)
        self.assertEqual(self.data, {})
        self.assertEqual(self.input.insert(0, self.stack)["count"], 4)
        self.assertEqual(self.output.extract(0, 3, True)["count"], 3)
        self.assertEqual(self.output.get_stack(0)["count"], 8)
        self.assertEqual(self.output.extract(0, 3)["count"], 3)
        self.assertEqual(self.input.get_stack(0)["count"], 5)
        self.assertEqual(self.input.insert(0, self.stack)["count"], 9)
        self.assertEqual(self.output.extract(0, 20)["count"], 8)
        self.assertIsNone(self.output.get_stack(0))

    def test_identity_permissions_and_metadata(self):
        self.assertEqual(self.input.get_slot_key(0), self.output.get_slot_key(0))
        self.assertEqual(self.output.insert(0, self.stack), self.stack)
        self.input.insert(0, dict(self.stack, count=2))
        self.assertIsNone(self.input.extract(0, 1))
        self.stack["userData"]["label"].append("b")
        self.assertEqual(self.input.insert(0, self.stack), self.stack)
        view = self.output.get_stack(0)
        view["userData"]["label"].append("c")
        self.assertEqual(self.output.extract(0, 2)["userData"], {"label": ["a"]})

    def test_unavailable_inventory(self):
        self.data = None
        self.assertEqual(self.input.insert(0, self.stack), self.stack)
        self.assertIsNone(self.output.extract(0, 1))
