def describe_chest(blocks, items, dimension, position):
    block = blocks.GetBlockNew(position, dimension)
    if not block or block.get("name") != "minecraft:chest":
        return ["Select a loaded ordinary chest."]

    paired = blocks.GetChestPairedPosition(position, dimension)
    positions = (position, tuple(paired)) if paired is not None else (position,)
    lines = []
    for pos in positions:
        size = items.GetContainerSize(pos, dimension)
        occupied = []
        if size in (27, 54):
            for slot in range(size):
                stack = items.GetContainerItem(pos, slot, dimension)
                if stack and stack.get("count"):
                    name = stack.get("newItemName") or stack.get("itemName")
                    occupied.append("%d=%s x%d" % (slot, name, stack["count"]))
        lines.append("pos=%s size=%s %s" % (pos, size, ", ".join(occupied) or "no items read"))
    return lines
