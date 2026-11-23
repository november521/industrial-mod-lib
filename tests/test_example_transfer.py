import json
from copy import deepcopy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from test_capabilities import EnergySystem, api


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
for side in ("source", "receiver"):
    sys.path.insert(0, str(EXAMPLES / side / "behavior_packs" / ("fe_" + side)))

with patch.dict(sys.modules, {
    "mod": types.ModuleType("mod"),
    "mod.server": types.ModuleType("mod.server"),
    api.__name__: api,
}):
    from IndustrialModLibFEReceiverScripts.server import BATTERY, PartialItemTestPort, ReceiverSystem
    from IndustrialModLibFESourceScripts.server import GENERATOR, SourceSystem


SOURCE_POS = (0, 65, 0)
BATTERY_POS = (0, 64, 0)
APPLE = {"newItemName": "minecraft:apple", "extraId": "iml:transfer_sample",
         "customTips": "IML Transfer Sample"}


class World:
    def __init__(self):
        self.data = {SOURCE_POS: {}, BATTERY_POS: {}}
        self.blocks = {SOURCE_POS: GENERATOR, BATTERY_POS: BATTERY}
        self.chest_stock = {}

    def CreateDimension(self, player):
        return self

    def GetPlayerDimensionId(self):
        return 0

    def GetBlockNew(self, position, dimension):
        name = self.blocks.get(position)
        return {"name": name} if name else None

    def GetBlockEntityData(self, dimension, position):
        return self.data.get(position)

    def GetContainerSize(self, position, dimension):
        return 27

    def GetChestPairedPosition(self, position, dimension):
        return None

    def GetItemBasicInfo(self, name, aux):
        return {"maxStackSize": 64}

    def GetContainerItem(self, position, slot, dimension, get_user_data):
        return deepcopy(self.chest_stock.get((position, slot)))

    def SpawnItemToContainer(self, stack, slot, position, dimension):
        self.chest_stock[position, slot] = deepcopy(stack)
        return True


class ExampleTransferTests(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.messages = []
        self.load_components()
        self.act("seed")

    def load_components(self):
        library = EnergySystem("fe", "energy")
        library._block_info = self.world
        library._block_entities = self.world
        library._items = self.world
        receiver = ReceiverSystem.__new__(ReceiverSystem)
        receiver._fe = None
        source = SourceSystem.__new__(SourceSystem)
        source._fe = None
        source._factory = self.world
        source._blocks = self.world
        source._panel_targets = {}
        source.NotifyToClient = lambda player, event, data: self.messages.append((event, data))
        with patch.object(api, "GetSystem", return_value=library, create=True):
            receiver.register_ports({})
            source.register_ports({})
        self.source = source
        self.library = library
        self.source.open_panel("player", SOURCE_POS)

    def act(self, action):
        self.source.on_transfer_action({"__id__": "player", "action": action})
        event, data = self.messages[-1]
        self.assertEqual(event, "TransferResult")
        return data["text"]

    def assert_stocks(self, source, battery, recovery=0):
        storage = self.source.storage_port(0, SOURCE_POS)
        output = self.library.get_block_capability(0, BATTERY_POS, "down", "item")
        for stack, count in ((storage.get_stack(0), source), (output.get_stack(0), battery),
                             (storage.get_stack(1), recovery)):
            self.assertEqual(stack, dict(APPLE, count=count) if count else None)

    def test_normal_transfer_and_full_battery(self):
        self.assertIn("Inventory unchanged", self.act("source"))
        self.assert_stocks(10, 0)
        self.assertIn("Planned: 8 / Moved: 8", self.act("send"))
        self.assert_stocks(2, 8)
        self.assertIn("Planned: 0 / Moved: 0", self.act("send"))
        self.assert_stocks(2, 8)

    def test_receiver_returns_unsent_items_from_the_full_offer(self):
        insert = PartialItemTestPort.insert
        offers = []

        def record(port, slot, stack, simulate=False):
            offers.append((stack["count"], simulate))
            return insert(port, slot, stack, simulate)

        with patch.object(PartialItemTestPort, "insert", record):
            self.assertIn("Planned: 8 / Moved: 4", self.act("partial"))
        self.assertEqual(offers, [(10, True), (8, False)])
        self.assert_stocks(6, 4)

        self.world.data = {pos: json.loads(json.dumps(stock))
                           for pos, stock in self.world.data.items()}
        self.load_components()
        self.assert_stocks(6, 4)
        self.source.open_panel("player", BATTERY_POS)
        self.assertEqual(self.act("source"), "Battery: Apple x4 [marked]")

    def test_rejected_return_goes_into_recovery_slot(self):
        def without_slot_zero_insert(dimension, position):
            return self.library.create_block_item_port(
                dimension, position, "iml_fe_source:items",
                {0: 16, 1: 16}, lambda stack: 64, (1,), ())

        with patch.object(self.source, "storage_port", without_slot_zero_insert):
            self.assertIn("Recovery: Apple x4 [marked]", self.act("partial"))
        self.assert_stocks(2, 4, 4)
        self.assertIn("Recovery slot occupied", self.act("send"))
        self.assert_stocks(2, 4, 4)
        self.assertIn("Recovery: Apple x4 [marked]", self.act("source"))

    def test_generator_to_chest_to_battery_preserves_stock_and_metadata(self):
        chest_pos = (1, 65, 0)
        battery_pos = (1, 64, 0)
        self.world.blocks.pop(BATTERY_POS)
        self.world.blocks[chest_pos] = "minecraft:chest"
        self.world.blocks[battery_pos] = BATTERY
        self.world.data[battery_pos] = {}
        self.assertIn("Preview: 10 item(s)", self.act("preview"))
        self.assertEqual(self.world.chest_stock, {})
        self.assertIn("Chest: Apple x10 [marked]", self.act("send"))
        self.source.open_panel("player", battery_pos)
        self.assertIn("Preview: 8 item(s)", self.act("preview"))
        chest = self.library.get_block_capability(0, chest_pos, "down", "item")
        battery = self.library.get_block_capability(0, battery_pos, "up", "item")
        self.assertEqual(chest.get_stack(0), dict(APPLE, count=10))
        self.assertIsNone(battery.get_stack(0))
        self.assertIn("Planned: 8 / Moved: 8", self.act("pull"))
        self.assertEqual(chest.get_stack(0), dict(APPLE, count=2))
        self.assertEqual(battery.get_stack(0), dict(APPLE, count=8))
        self.assertIn("Planned: 0 / Moved: 0", self.act("pull"))
        self.assertEqual(chest.get_stack(0), dict(APPLE, count=2))
