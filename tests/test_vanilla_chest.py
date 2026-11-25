from copy import deepcopy
import unittest

from test_capabilities import EnergySystem
from IndustrialModLibScripts.vanilla.chest import CHEST_IDS
from IndustrialModLibScripts.vanilla.container import BARREL, SHULKER_BOXES


POSITION = (1, 64, 3)
OTHER = (2, 64, 3)
DIMENSION = 2
APPLES = {"newItemName": "minecraft:apple", "extraId": "sample", "count": 10}


class NativeChest:
    def __init__(self):
        self.block = {"name": "minecraft:chest"}
        self.pair = None
        self.size = 27
        self.stock = {}
        self.writes = []
        self.reject_writes = False
        self.other_loaded = False
        self.other_block = None
        self.reciprocal_pair = True

    def GetBlockNew(self, position, dimension):
        if (position, dimension) == (POSITION, DIMENSION):
            return self.block
        if (position, dimension) == (OTHER, DIMENSION) and self.other_loaded:
            return self.other_block if self.other_block is not None else self.block

    def GetContainerSize(self, position, dimension):
        return self.size

    def GetChestPairedPosition(self, position, dimension):
        if position == OTHER:
            return POSITION if self.pair == OTHER and self.reciprocal_pair else None
        return self.pair

    def GetItemBasicInfo(self, name, aux):
        if name == "minecraft:apple":
            return {"maxStackSize": 64}
        if name == "minecraft:bow":
            return {"maxStackSize": 1}

    def GetContainerItem(self, position, slot, dimension, get_user_data):
        assert position == POSITION and dimension == DIMENSION and get_user_data
        return deepcopy(self.stock.get(slot))

    def SpawnItemToContainer(self, stack, slot, position, dimension):
        assert position == POSITION and dimension == DIMENSION
        self.writes.append((slot, stack))
        if self.reject_writes:
            return False
        self.stock[slot] = deepcopy(stack)
        return True


class ChestCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.chest = NativeChest()
        self.library = EnergySystem("fe", "energy")
        self.library._block_info = self.chest
        self.library._items = self.chest

    def port(self, face="up"):
        return self.library.get_block_capability(DIMENSION, POSITION, face, "item")

    def test_faces_share_slots_and_simulation_does_not_write(self):
        top, side = self.port(), self.port("west")
        self.assertEqual(top.get_slots(), tuple(range(27)))
        self.assertEqual(top.get_slot_key(0), side.get_slot_key(0))
        self.assertNotEqual(top.get_slot_key(0), side.get_slot_key(1))
        self.assertIsNone(top.insert(26, APPLES, simulate=True))
        self.assertEqual(self.chest.writes, [])
        self.assertIsNone(top.insert(26, APPLES))
        self.assertEqual(side.extract(26, 3, simulate=True), dict(APPLES, count=3))
        self.assertEqual(side.get_stack(26), APPLES)
        self.assertEqual(side.extract(26, 10), APPLES)
        self.assertEqual(self.chest.stock[26], {})
        self.assertIsNone(top.get_stack(26))

    def test_sdk_aliases_can_merge_but_metadata_and_item_limits_apply(self):
        self.chest.stock[0] = {"itemName": "minecraft:apple", "auxValue": 0, "count": 62,
                              "durability": 0, "enchantData": [], "extraId": "sample"}
        port = self.port()
        self.assertEqual(port.insert(0, dict(APPLES, extraId="different")),
                         dict(APPLES, extraId="different"))
        self.assertEqual(port.insert(0, APPLES), dict(APPLES, count=8))
        self.assertEqual(port.get_stack(0), dict(APPLES, count=64))
        bow = {"newItemName": "minecraft:bow", "count": 2,
               "enchantData": [(1, 2)], "userData": {"display": {"Name": "Sample bow"}}}
        self.assertEqual(port.insert(1, bow), dict(bow, count=1))
        extracted = port.extract(1, 1)
        self.assertEqual(extracted, dict(bow, count=1, enchantData=[[1, 2]]))
        self.assertIsNone(port.insert(2, extracted))
        self.assertEqual(self.chest.stock[2]["enchantData"], [(1, 2)])

    def test_failed_writes_report_no_transfer(self):
        self.chest.stock[0] = APPLES.copy()
        self.chest.reject_writes = True
        port = self.port()
        self.assertEqual(port.insert(0, APPLES), APPLES)
        self.assertIsNone(port.extract(0, 2))
        self.assertEqual(port.get_stack(0), APPLES)

    def test_pairing_and_unavailability_invalidate_operations(self):
        port = self.port()
        self.chest.pair = (2, 64, 3)
        self.assertIsNone(self.port())
        self.assertEqual(port.insert(0, APPLES), APPLES)
        self.assertIsNone(port.extract(0, 1))
        self.chest.pair = None
        self.assertIsNotNone(self.port())
        self.assertEqual(port.insert(0, APPLES), APPLES)
        self.chest.size = 54
        self.assertIsNone(self.port())
        self.chest.size = 27
        self.chest.block = None
        self.assertIsNone(self.port())
        self.assertIsNone(port.get_stack(0))
        self.assertEqual(self.chest.writes, [])

    def test_double_chest_shares_inventory_across_halves_and_faces(self):
        single = self.port()
        self.chest.other_loaded = True
        self.chest.size = 54
        self.chest.pair = OTHER
        first = self.port("west")
        second = self.library.get_block_capability(DIMENSION, OTHER, "up", "item")
        self.assertEqual(first.get_slots(), tuple(range(54)))
        self.assertEqual(first.get_slot_key(27), second.get_slot_key(27))
        self.assertNotEqual(first.get_slot_key(0), first.get_slot_key(27))
        self.assertEqual(single.insert(0, APPLES), APPLES)
        self.assertIsNone(second.insert(27, APPLES, True))
        self.assertEqual(self.chest.writes, [])
        self.assertIsNone(second.insert(27, APPLES))
        self.assertEqual(first.extract(27, 4), dict(APPLES, count=4))
        self.assertEqual(second.get_stack(27), dict(APPLES, count=6))
        self.chest.other_loaded = False
        self.assertEqual(first.insert(27, APPLES), APPLES)
        self.assertIsNone(second.extract(27, 1))
        self.chest.pair = None
        self.chest.size = 27
        self.assertEqual(self.port().get_slots(), tuple(range(27)))
        self.assertIsNone(first.extract(27, 1))

    def test_each_chest_variant_supports_single_and_double_slot_access(self):
        self.assertEqual(set(CHEST_IDS), {
            "minecraft:chest", "minecraft:trapped_chest",
            "minecraft:copper_chest", "minecraft:exposed_copper_chest",
            "minecraft:weathered_copper_chest", "minecraft:oxidized_copper_chest",
            "minecraft:waxed_copper_chest", "minecraft:waxed_exposed_copper_chest",
            "minecraft:waxed_weathered_copper_chest", "minecraft:waxed_oxidized_copper_chest",
        })
        for identifier in CHEST_IDS:
            with self.subTest(identifier=identifier):
                self.chest.block = {"name": identifier}
                self.chest.size = 27
                self.chest.pair = None
                single = self.port()
                self.assertEqual(single.get_slots(), tuple(range(27)))
                self.assertIsNone(single.insert(26, APPLES))
                self.assertEqual(single.extract(26, 10), APPLES)

                self.chest.other_loaded = True
                self.chest.size = 54
                self.chest.pair = OTHER
                first = self.port()
                second = self.library.get_block_capability(DIMENSION, OTHER, "up", "item")
                self.assertEqual(first.get_slots(), tuple(range(54)))
                self.assertEqual(first.get_slot_key(53), second.get_slot_key(53))
                self.assertIsNone(second.insert(53, APPLES))
                self.assertEqual(first.extract(53, 10), APPLES)
                self.assertIsNone(second.get_stack(53))

    def test_copper_pair_requires_supported_halves_and_matching_links(self):
        self.chest.block = {"name": "minecraft:copper_chest"}
        self.chest.other_loaded = True
        self.chest.size = 54
        self.chest.pair = OTHER
        self.chest.reciprocal_pair = False
        self.assertIsNone(self.port())
        self.chest.reciprocal_pair = True
        self.chest.other_block = {"name": "minecraft:ender_chest"}
        self.assertIsNone(self.port())
        self.assertIsNone(self.library.get_block_capability(DIMENSION, OTHER, "up", "item"))
        self.assertEqual(self.chest.writes, [])

    def test_copper_variant_change_invalidates_cached_port_and_preserves_stock(self):
        self.chest.block = {"name": "minecraft:weathered_copper_chest"}
        self.chest.other_loaded = True
        self.chest.size = 54
        self.chest.pair = OTHER
        old = self.port()
        self.assertIsNone(old.insert(27, APPLES))

        self.chest.other_block = {"name": "minecraft:waxed_weathered_copper_chest"}
        self.assertIsNone(old.extract(27, 1))
        new = self.port()
        other = self.library.get_block_capability(DIMENSION, OTHER, "up", "item")
        self.assertEqual(new.get_slot_key(27), old.get_slot_key(27))
        self.assertEqual(other.get_slot_key(27), new.get_slot_key(27))
        self.assertEqual(other.extract(27, 4), dict(APPLES, count=4))
        self.assertEqual(new.get_stack(27), dict(APPLES, count=6))

    def test_barrel_and_all_shulker_ids_use_single_container_slots(self):
        for identifier in (BARREL,) + SHULKER_BOXES:
            with self.subTest(identifier=identifier):
                self.chest.block = {"name": identifier}
                top, side = self.port(), self.port("west")
                self.assertEqual(top.get_slots(), tuple(range(27)))
                self.assertEqual(top.get_slot_key(26), side.get_slot_key(26))
                self.assertIsNone(top.insert(26, APPLES))
                self.assertEqual(side.extract(26, 10), APPLES)

    def test_single_container_port_invalidates_on_block_replacement(self):
        self.chest.block = {"name": BARREL}
        barrel = self.port()
        self.chest.block = {"name": "minecraft:white_shulker_box"}
        self.assertEqual(barrel.insert(0, APPLES), APPLES)
        self.assertEqual(self.chest.writes, [])
        self.assertIsNone(self.port().insert(0, APPLES))
