from copy import deepcopy

from IndustrialModLibScripts.items import ItemPort


CHEST = "minecraft:chest"
ENCHANTMENT_FIELDS = ("enchantData", "modEnchantData")


def _canonical_stack(stack):
    """Normalize SDK aliases and defaults while preserving item metadata."""
    item = deepcopy(stack)
    name = item.get("newItemName") or item.get("itemName")
    aux = item.get("newAuxValue", item.get("auxValue", 0))
    item.pop("itemName", None)
    item.pop("auxValue", None)
    item["newItemName"] = name
    if aux:
        item["newAuxValue"] = aux
    else:
        item.pop("newAuxValue", None)
    for field, default in (("durability", 0), ("showInHand", True), ("extraId", ""),
                           ("customTips", ""), ("userData", {})):
        if item.get(field) in (None, default):
            item.pop(field, None)
    for field in ENCHANTMENT_FIELDS:
        if item.get(field):
            # Custom block storage supports lists, including nested lists.
            item[field] = [list(enchantment) for enchantment in item[field]]
        else:
            item.pop(field, None)
    return item


def _chest_positions(blocks, items, dimension, position):
    block = blocks.GetBlockNew(position, dimension)
    if not block or block.get("name") != CHEST:
        return ()
    size = items.GetContainerSize(position, dimension)
    linked = blocks.GetChestPairedPosition(position, dimension)
    if linked is None:
        return (position,) if size == 27 else ()
    other = tuple(linked)
    if (size != 54 or other[1] != position[1]
            or abs(other[0] - position[0]) + abs(other[2] - position[2]) != 1):
        return ()
    block = blocks.GetBlockNew(other, dimension)
    if not block or block.get("name") != CHEST or items.GetContainerSize(other, dimension) != 54:
        return ()
    backlink = blocks.GetChestPairedPosition(other, dimension)
    if backlink is None or tuple(backlink) != position:
        return ()
    return tuple(sorted((position, other)))


def open_chest(blocks, items, dimension, position):
    position = tuple(position)
    positions = _chest_positions(blocks, items, dimension, position)
    if not positions:
        return None
    return ChestItemPort(blocks, items, dimension, position, positions)


class ChestItemPort(ItemPort):
    def __init__(self, blocks, items, dimension, position, positions):
        self._blocks = blocks
        self._items = items
        self._dimension = dimension
        self._entry = position
        self._positions = positions
        # Use the same SDK access point and slot ordering from either face or half.
        self._position = positions[0]
        slots = tuple(range(27 * len(positions)))
        self._valid = True
        ItemPort.__init__(self, self._resolve_chest, (dimension, positions, CHEST),
                          dict.fromkeys(slots, 64), self._stack_limit, slots, slots)

    def _resolve_chest(self):
        if not self._valid:
            return None
        if _chest_positions(self._blocks, self._items, self._dimension,
                            self._entry) == self._positions:
            return self._items
        self._valid = False
        return None

    def _stack_limit(self, stack):
        name = stack.get("newItemName") or stack.get("itemName")
        if not name or name == "minecraft:air":
            return 0
        aux = stack.get("newAuxValue", stack.get("auxValue", 0))
        info = self._items.GetItemBasicInfo(name, aux)
        return info.get("maxStackSize", 0) if info else 0

    def _read(self, items, slot):
        if items is None:
            return None
        stack = items.GetContainerItem(self._position, slot, self._dimension, True)
        if not stack or not stack.get("count"):
            return None
        stack = _canonical_stack(stack)
        return stack if stack["newItemName"] != "minecraft:air" else None

    def _write(self, items, slot, stack):
        item = {}
        if stack is not None:
            item = _canonical_stack(stack)
            item.setdefault("newAuxValue", 0)
            for field in ENCHANTMENT_FIELDS:
                if field in item:
                    item[field] = [tuple(enchantment) for enchantment in item[field]]
        return items.SpawnItemToContainer(item, slot, self._position, self._dimension)

    @staticmethod
    def _same_item(first, second):
        return ItemPort._same_item(_canonical_stack(first), _canonical_stack(second))
