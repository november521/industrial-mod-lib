import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "behavior_packs" / "industrial_mod_lib"))
sys.path.insert(0, str(ROOT / "examples" / "source" / "behavior_packs" / "fe_source"))

from IndustrialModLibFESourceScripts.item_batch import run_item_batch, run_item_gather
from IndustrialModLibScripts.items import ItemPort


STACK = {
    "newItemName": "minecraft:apple",
    "newAuxValue": 0,
    "extraId": "iml:batch_test",
    "userData": {"labels": ["batch"]},
}


class SplitView:
    def __init__(self, simulated, actual, extract_limit=64):
        self.simulated = simulated
        self.actual = actual
        self.extract_limit = extract_limit
        self.offers = []

    def get_slots(self):
        return self.actual.get_slots()

    def get_slot_key(self, slot):
        return self.actual.get_slot_key(slot)

    def insert(self, slot, stack, simulate=False):
        if simulate:
            return self.simulated.insert(slot, stack, simulate=True)
        self.offers.append(stack["count"])
        return self.actual.insert(slot, stack)

    def extract(self, slot, count, simulate=False):
        if simulate:
            return self.simulated.extract(slot, count, simulate=True)
        return self.actual.extract(slot, min(count, self.extract_limit))


class ItemBatchTests(unittest.TestCase):
    def setUp(self):
        self.inventories = {}
        self.source = self.port("source", {0: 16})
        self.recovery = self.port("recovery", {0: 16})
        self.source.insert(0, dict(STACK, count=10))

    def port(self, key, limits, insert=True, extract=True):
        data = self.inventories.setdefault(key, {})
        return ItemPort(lambda: data, key, limits, lambda stack: 64,
                        limits if insert else (), limits if extract else ())

    def assert_stock(self, port, count, slot=0):
        self.assertEqual(port.get_stack(slot), dict(STACK, count=count) if count else None)

    def test_preview_does_not_mutate_and_execution_splits_ten(self):
        first = self.port("first", {0: 4})
        second = self.port("second", {0: 16})
        targets = [first, None, second]
        preview = run_item_batch(self.source, self.source, None, targets, simulate=True)
        self.assertEqual(preview, {"planned": (4, 0, 6), "moved": (0, 0, 0),
                                   "scanned": 2, "restored": 0, "buffered": 0})
        self.assert_stock(self.source, 10)
        self.assert_stock(first, 0)
        self.assert_stock(second, 0)

        actual = run_item_batch(self.source, self.source, self.recovery, targets)
        self.assertEqual(actual, dict(preview, moved=(4, 0, 6)))
        self.assert_stock(self.source, 0)
        self.assert_stock(first, 4)
        self.assert_stock(second, 6)
        self.assert_stock(self.recovery, 0)

    def test_slot_identity_allows_an_insertable_face_and_deduplicates_it(self):
        same_as_source = self.port("source", {0: 16})
        blocked = self.port("first", {0: 4}, insert=False)
        first = self.port("first", {0: 4})
        alias = self.port("first", {0: 4})
        second = self.port("second", {0: 16})
        result = run_item_batch(self.source, self.source, self.recovery,
                                [same_as_source, blocked, first, alias, second])
        self.assertEqual(result["scanned"], 5)
        self.assertEqual(result["planned"], (0, 0, 4, 0, 6))
        self.assertEqual(result["moved"], result["planned"])
        self.assert_stock(self.source, 0)
        self.assert_stock(first, 4)
        self.assert_stock(alias, 4)
        self.assert_stock(second, 6)

    def test_round_respects_slot_and_item_budgets(self):
        first = self.port("first", {0: 2, 1: 3, 2: 16})
        second = self.port("second", {0: 16})
        result = run_item_batch(self.source, self.source, self.recovery,
                                [first, second], max_slots=2)
        self.assertEqual(result["scanned"], 2)
        self.assertEqual(result["moved"], (5, 0))
        self.assert_stock(first, 2)
        self.assert_stock(first, 3, slot=1)
        self.assert_stock(first, 0, slot=2)
        self.assert_stock(self.source, 5)

        result = run_item_batch(self.source, self.source, self.recovery,
                                [second, first], max_items=3)
        self.assertEqual(result["scanned"], 1)
        self.assertEqual(result["moved"], (3, 0))
        self.assert_stock(second, 3)
        self.assert_stock(self.source, 2)

    def test_partial_writes_restore_then_buffer_the_typed_remainder(self):
        source = SplitView(self.source, self.source, extract_limit=7)
        restore = self.port("source", {0: 4})
        first = SplitView(self.port("first", {0: 4}), self.port("first", {0: 1}))
        second_port = self.port("second", {0: 16})
        second = SplitView(second_port, second_port)
        result = run_item_batch(source, restore, self.recovery, [first, second])
        self.assertEqual(result, {"planned": (4, 6), "moved": (1, 3),
                                  "scanned": 2, "restored": 1, "buffered": 2})
        self.assertEqual(first.offers, [4])
        self.assertEqual(second.offers, [3])
        self.assert_stock(first.actual, 1)
        self.assert_stock(second_port, 3)
        self.assert_stock(restore, 4)
        self.assert_stock(self.recovery, 2)

    def test_execution_leaves_items_in_place_when_recovery_is_incompatible(self):
        target = self.port("target", {0: 16})
        existing = {"newItemName": "minecraft:stone", "count": 1}
        self.recovery.insert(0, existing)
        result = run_item_batch(self.source, self.source, self.recovery, [target])
        self.assertEqual(result, {"planned": (10,), "moved": (0,), "scanned": 1,
                                  "restored": 0, "buffered": 0})
        self.assert_stock(self.source, 10)
        self.assert_stock(target, 0)
        self.assertEqual(self.recovery.get_stack(0), existing)

    def test_gather_excludes_aliases_and_the_destination_from_source_slots(self):
        self.source.extract(0, 5)
        alias = self.port("source", {0: 16})
        target = self.port("target", {0: 16})
        target.insert(0, dict(STACK, count=1))
        sources = (target, None, self.source, alias)
        preview = run_item_gather(sources, target, self.recovery, simulate=True)
        self.assertEqual(preview["planned"], (0, 0, 5, 0))
        self.assert_stock(self.source, 5)
        self.assert_stock(target, 1)

        result = run_item_gather(sources, target, self.recovery)
        self.assertEqual(result["moved"], (0, 0, 5, 0))
        self.assert_stock(self.source, 0)
        self.assert_stock(target, 6)

    def test_gather_returns_rejected_items_to_the_second_source(self):
        self.source.extract(0, 5)
        east = self.port("east", {0: 16})
        east.insert(0, dict(STACK, count=5))
        battery = SplitView(self.port("battery", {0: 8}), self.port("battery", {0: 6}))
        result = run_item_gather((self.source, east), battery, self.recovery)
        self.assertEqual(result["planned"], (5, 3))
        self.assertEqual(result["moved"], (5, 1))
        self.assertEqual(result["returned"], 2)
        self.assert_stock(self.source, 0)
        self.assert_stock(east, 4)
        self.assert_stock(battery.actual, 6)
        self.assert_stock(self.recovery, 0)

    def test_gather_buffers_when_source_cannot_restore_and_stops_when_buffer_cannot_accept(self):
        source = self.port("source", {0: 16}, insert=False)
        target = SplitView(self.port("target", {0: 8}), self.port("target", {0: 1}))
        result = run_item_gather((source,), target, self.recovery)
        self.assertEqual(result["moved"], (1,))
        self.assert_stock(source, 2)
        self.assert_stock(target.actual, 1)
        self.assert_stock(self.recovery, 7)

        result = run_item_gather((source,), target, self.port("recovery", {0: 8}))
        self.assertTrue(result["recovery_blocked"])
        self.assertEqual(result["moved"], (0,))
        self.assert_stock(source, 2)
        self.assert_stock(self.recovery, 7)
