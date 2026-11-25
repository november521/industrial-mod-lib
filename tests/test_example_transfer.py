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
    from IndustrialModLibFESourceScripts.batch_demo import CONDUIT
    from IndustrialModLibFESourceScripts.chest_probe import describe_chest
    from IndustrialModLibFESourceScripts.fluid_demo import TANK
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

    def CreatePos(self, player):
        return self

    def GetFootPos(self):
        return SOURCE_POS

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

    def GetContainerItem(self, position, slot, dimension, get_user_data=False):
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
        self.assertIn("Target: Apple x10 [marked]", self.act("send"))
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

    def test_generator_can_send_to_copper_chest_and_battery_can_pull_from_it(self):
        chest_pos, battery_pos = (1, 65, 0), (1, 64, 0)
        self.world.blocks.pop(BATTERY_POS)
        self.world.blocks.update({chest_pos: "minecraft:waxed_oxidized_copper_chest",
                                  battery_pos: BATTERY})
        self.world.data[battery_pos] = {}
        self.assertIn("Preview: 10 item(s)", self.act("preview"))
        self.assertEqual(self.world.chest_stock, {})
        self.assertIn("Planned: 10 / Moved: 10", self.act("send"))
        self.source.open_panel("player", battery_pos)
        self.assertIn("Preview: 8 item(s)", self.act("preview"))
        self.assertIn("Planned: 8 / Moved: 8", self.act("pull"))
        chest = self.library.get_block_capability(0, chest_pos, "down", "item")
        self.assertEqual(chest.get_stack(0), dict(APPLE, count=2))

    def test_chest_probe_reports_raw_and_registered_copper_slots(self):
        copper, other = (1, 65, 0), (2, 65, 0)
        self.world.blocks.update(dict.fromkeys((copper, other), "minecraft:copper_chest"))
        pairs = {copper: other, other: copper}
        self.world.GetChestPairedPosition = lambda pos, dimension: pairs.get(pos)
        self.world.GetContainerSize = lambda pos, dimension: 54 if pos in pairs else -1
        for pos in pairs:
            self.world.chest_stock[pos, 27] = dict(APPLE, count=2)
        lines = describe_chest(self.world, self.world, 0, copper,
                               self.library.get_block_capability)
        self.assertEqual(len(lines), 2)
        self.assertIn("block=minecraft:copper_chest paired=(2, 65, 0)", lines[0])
        for line in lines:
            self.assertIn("size=54 iml_slots=54 27=minecraft:apple x2", line)

    def test_generator_batch_distributes_to_battery_and_chest_in_one_round(self):
        conduit_pos, battery_pos, chest_pos = BATTERY_POS, (0, 63, 0), (1, 64, 0)
        self.world.blocks.update({conduit_pos: CONDUIT, battery_pos: BATTERY,
                                  chest_pos: "minecraft:chest"})
        self.world.data[battery_pos] = {}
        battery = self.library.get_block_capability(0, battery_pos, "up", "item")
        chest = self.library.get_block_capability(0, chest_pos, "west", "item")
        generator = self.source.storage_port(0, SOURCE_POS)
        self.assertIsNone(battery.insert(0, dict(APPLE, count=4)))
        self.source.open_panel("player", SOURCE_POS)
        self.assertEqual(self.messages[-1], ("OpenTransferPanel", {"mode": "batch"}))

        before_preview = deepcopy(self.world.data)
        preview = self.act("preview")
        self.assertIn("Down: 4 planned", preview)
        self.assertIn("East: 6 planned", preview)
        self.assertEqual(self.world.data, before_preview)
        self.assertEqual(self.world.chest_stock, {})

        result = self.act("send")
        self.assertIn("Down: 4 moved / 4 planned", result)
        self.assertIn("East: 6 moved / 6 planned", result)
        self.assertIn("Generator: 0   Recovery: 0", result)
        self.assertEqual(battery.get_stack(0), dict(APPLE, count=8))
        self.assertEqual(chest.get_stack(0), dict(APPLE, count=6))
        self.assertIsNone(generator.get_stack(0))
        self.assertIn("East: 0 moved / 0 planned", self.act("send"))
        self.assertEqual(chest.get_stack(0), dict(APPLE, count=6))

    def set_up_item_gathering(self, west_stack, east_stack, west_name="minecraft:chest",
                              east_name="minecraft:chest", target_name=BATTERY):
        west, east = (-1, 65, 0), (1, 65, 0)
        self.world.blocks.update({
            SOURCE_POS: CONDUIT, west: west_name, east: east_name, BATTERY_POS: target_name,
        })
        self.world.chest_stock[west, 0] = west_stack
        self.world.chest_stock[east, 0] = east_stack
        self.source.on_transfer_action(
            {"__id__": "player", "action": "open", "position": list(SOURCE_POS)})
        self.assertEqual(self.messages[-1], ("OpenTransferPanel", {"mode": "gather"}))
        return (
            self.library.get_block_capability(0, west, "east", "item"),
            self.library.get_block_capability(0, east, "west", "item"),
            self.library.get_block_capability(0, BATTERY_POS, "up", "item"),
        )

    def test_item_gathering_shares_capacity_without_writing_in_preview(self):
        five_apples = dict(APPLE, count=5)
        west, east, battery = self.set_up_item_gathering(five_apples, five_apples)
        self.assertIn("West: 5 in first slot", self.act("source"))
        preview = self.act("preview")
        self.assertIn("West: 5 planned", preview)
        self.assertIn("East: 3 planned", preview)
        self.assertEqual(west.get_stack(0), five_apples)
        self.assertEqual(east.get_stack(0), five_apples)
        self.assertIsNone(battery.get_stack(0))

        result = self.act("send")
        self.assertIn("West: 5 moved / 5 planned", result)
        self.assertIn("East: 3 moved / 3 planned", result)
        self.assertIn("Battery: 8   Recovery: 0", result)
        self.assertIsNone(west.get_stack(0))
        self.assertEqual(east.get_stack(0), dict(APPLE, count=2))
        self.assertEqual(battery.get_stack(0), dict(APPLE, count=8))
        self.assertIn("East: 0 moved / 0 planned", self.act("send"))
        self.assertEqual(east.get_stack(0), dict(APPLE, count=2))

    def test_item_gathering_keeps_incompatible_stacks_in_their_chest(self):
        five_apples = dict(APPLE, count=5)
        five_stones = {"newItemName": "minecraft:cobblestone", "count": 5}
        west, east, battery = self.set_up_item_gathering(five_apples, five_stones)
        self.assertIn("East: 0 planned", self.act("preview"))
        self.assertIn("East: 0 moved / 0 planned", self.act("send"))
        self.assertIsNone(west.get_stack(0))
        self.assertEqual(east.get_stack(0), five_stones)
        self.assertEqual(battery.get_stack(0), five_apples)

    def test_item_gathering_uses_barrel_and_shulker_box_as_sources(self):
        five_apples = dict(APPLE, count=5)
        west, east, battery = self.set_up_item_gathering(
            five_apples, five_apples, west_name="minecraft:barrel",
            east_name="minecraft:light_gray_shulker_box")
        preview = self.act("preview")
        self.assertIn("West: 5 planned", preview)
        self.assertIn("East: 3 planned", preview)
        self.assertEqual(west.get_stack(0), five_apples)
        self.assertEqual(east.get_stack(0), five_apples)
        self.assertIsNone(battery.get_stack(0))

        self.act("send")
        self.assertIsNone(west.get_stack(0))
        self.assertEqual(east.get_stack(0), dict(five_apples, count=2))
        self.assertEqual(battery.get_stack(0), dict(five_apples, count=8))

    def test_item_gathering_preserves_loaded_shulker_and_rejects_nesting(self):
        loaded_box = {
            "newItemName": "minecraft:blue_shulker_box",
            "count": 1,
            "userData": {"Items": [{"Name": {"type": 8, "value": "minecraft:apple"},
                                    "Count": {"type": 1, "value": 2},
                                    "Slot": {"type": 1, "value": 8}}]},
        }
        west, _, target = self.set_up_item_gathering(
            loaded_box, None, west_name="minecraft:barrel",
            target_name="minecraft:undyed_shulker_box")
        self.assertIn("West: 0 planned", self.act("preview"))
        self.assertIn("West: 0 moved", self.act("send"))
        self.assertEqual(west.get_stack(0), loaded_box)
        self.assertIsNone(target.get_stack(0))

        self.world.blocks[BATTERY_POS] = "minecraft:chest"
        chest = self.library.get_block_capability(0, BATTERY_POS, "up", "item")
        self.assertIn("West: 1 planned", self.act("preview"))
        self.assertIn("West: 1 moved", self.act("send"))
        self.assertIsNone(west.get_stack(0))
        self.assertEqual(chest.get_stack(0), loaded_box)
        self.assertEqual(chest.insert(0, loaded_box), loaded_box)
        self.assertEqual(chest.get_stack(0), loaded_box)
        self.assertEqual(chest.extract(0, 1), loaded_box)

    def test_item_gathering_can_insert_into_a_placed_shulker(self):
        five_apples = dict(APPLE, count=5)
        west, _, target = self.set_up_item_gathering(
            five_apples, None, target_name="minecraft:undyed_shulker_box")
        self.assertIn("West: 5 moved", self.act("send"))
        self.assertIsNone(west.get_stack(0))
        self.assertEqual(target.get_stack(0), five_apples)

    def test_item_gathering_can_use_a_registered_nonzero_source_slot(self):
        crate = "sample:crate"
        crate_pos = (-1, 65, 0)
        stock = dict(APPLE, count=4)
        self.world.data[crate_pos] = {}
        self.library.register_block_capability(
            crate, "item", lambda dim, pos, face: self.library.create_block_item_port(
                dim, pos, crate, {5: 16}, None, (5,), (5,)) if face == "east" else None)
        source, _, battery = self.set_up_item_gathering(None, None, west_name=crate)
        self.assertIsNone(source.insert(5, stock))
        self.assertIn("West: 4 planned", self.act("preview"))
        self.assertIn("West: 4 moved", self.act("send"))
        self.assertIsNone(source.get_stack(5))
        self.assertEqual(battery.get_stack(0), stock)

    def test_fluid_demo_moves_water_and_lava_through_registered_faces(self):
        first, second = BATTERY_POS, (0, 63, 0)
        for position in (first, second):
            self.world.blocks[position] = TANK
            self.world.data[position] = {}
        water, lava = "minecraft:water", "minecraft:lava"
        self.source.open_panel("player", SOURCE_POS)
        self.assertEqual(self.messages[-1], ("OpenTransferPanel", {"mode": "fluid_source"}))

        source = self.library.get_block_capability(0, SOURCE_POS, "down", "fluid")
        inlet = self.library.get_block_capability(0, first, "up", "fluid")
        outlet = self.library.get_block_capability(0, first, "down", "fluid")
        second_outlet = self.library.get_block_capability(0, second, "down", "fluid")
        self.assertIsNone(self.library.get_block_capability(0, first, "east", "fluid"))
        self.assertEqual(source.fill(water, 10), 0)
        self.assertEqual(outlet.fill(water, 10), 0)
        self.assertIn("Loaded 1500 mB of Water", self.act("seed"))
        self.assertIn("Preview: 1000 mB", self.act("preview"))
        self.assertEqual(source.get_fluid(), (water, 1500))
        self.assertIsNone(inlet.get_fluid())
        self.assertIn("Moved: 1000 / 1000 mB", self.act("send"))
        self.assertEqual(source.get_fluid(), (water, 500))
        self.assertEqual(inlet.get_fluid(), (water, 1000))
        self.assertEqual(inlet.drain(water, 10), 0)
        self.assertIn("Moved: 0 / 0 mB", self.act("send"))
        self.assertIn("Send the remaining fluid", self.act("partial"))

        self.source.open_panel("player", first)
        self.assertEqual(self.messages[-1], ("OpenTransferPanel", {"mode": "tank"}))
        self.assertIn("Moved: 1000 / 1000 mB", self.act("send"))
        self.assertIsNone(outlet.get_fluid())
        self.assertEqual(second_outlet.get_fluid(), (water, 1000))

        self.source.open_panel("player", SOURCE_POS)
        self.assertIn("Moved: 500 / 500 mB", self.act("send"))
        self.assertIn("Loaded 1500 mB of Lava", self.act("partial"))
        self.assertIn("Moved: 0 / 0 mB", self.act("send"))
        self.assertEqual(inlet.get_fluid(), (water, 500))
        self.assertEqual(source.get_fluid(), (lava, 1500))
        self.assertEqual(outlet.drain(water, 500), 500)
        self.assertIsNone(inlet.get_fluid())
        self.assertIn("Moved: 1000 / 1000 mB", self.act("send"))

        self.world.data = {pos: json.loads(json.dumps(stock))
                           for pos, stock in self.world.data.items()}
        self.load_components()
        self.source.open_panel("player", first)
        self.assertIn("Tank: Lava 1000/1000 mB", self.act("source"))
        self.source.open_panel("player", SOURCE_POS)
        self.assertIn("Generator: Lava 500/1500 mB", self.act("source"))
        self.assertIn("Tank below: Lava 1000/1000 mB", self.act("source"))
