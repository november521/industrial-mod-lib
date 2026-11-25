from copy import deepcopy

from IndustrialModLibScripts.items import ItemPort


BARREL = "minecraft:barrel"
SHULKER_BOXES = ("minecraft:shulker_box", "minecraft:undyed_shulker_box") + tuple(
    "minecraft:%s_shulker_box" % color
    for color in ("white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray",
                  "light_gray", "cyan", "purple", "blue", "brown", "green", "red", "black")
)
SINGLE_CONTAINERS = (BARREL,) + SHULKER_BOXES
ENCHANTMENT_FIELDS = ("enchantData", "modEnchantData")


def _item_name(stack):
    return stack.get("newItemName") or stack.get("itemName")


def item_stack_limit(items, stack):
    name = _item_name(stack)
    if not name or name == "minecraft:air":
        return 0
    if name in SHULKER_BOXES:
        return 1
    aux = stack.get("newAuxValue", stack.get("auxValue", 0))
    info = items.GetItemBasicInfo(name, aux)
    return info.get("maxStackSize", 0) if info else 0


def _canonical_stack(stack):
    """Normalize SDK aliases and defaults while preserving item metadata."""
    item = deepcopy(stack)
    name = _item_name(item)
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


def open_single_container(blocks, items, dimension, position):
    position = tuple(position)
    block = blocks.GetBlockNew(position, dimension)
    name = block.get("name") if block else None
    if name not in SINGLE_CONTAINERS:
        return None

    def resolve_positions():
        current = blocks.GetBlockNew(position, dimension)
        if current and current.get("name") == name and items.GetContainerSize(position, dimension) == 27:
            return (position,)
        return ()

    positions = resolve_positions()
    if not positions:
        return None
    return ContainerItemPort(items, dimension, name, positions, resolve_positions)


class ContainerItemPort(ItemPort):
    def __init__(self, items, dimension, identifier, positions, resolve_positions):
        self._items = items
        self._dimension = dimension
        self._positions = positions
        self._resolve_positions = resolve_positions
        self._reject_shulkers = identifier in SHULKER_BOXES
        # Use the same SDK access point and slot ordering from either half of a double chest.
        self._position = positions[0]
        slots = tuple(range(27 * len(positions)))
        ItemPort.__init__(self, self._resolve_container, (dimension, positions, identifier),
                          dict.fromkeys(slots, 64), self._stack_limit, slots, slots)

    def _resolve_container(self):
        if self._resolve_positions is not None and self._resolve_positions() == self._positions:
            return self._items
        self._resolve_positions = None
        return None

    def insert(self, slot, stack, simulate=False):
        if (self._reject_shulkers and stack and _item_name(stack) in SHULKER_BOXES
                and self._count(stack["count"])):
            self.get_slot_limit(slot)
            return deepcopy(stack)
        return ItemPort.insert(self, slot, stack, simulate)

    def _stack_limit(self, stack):
        return item_stack_limit(self._items, stack)

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
