def describe_chest(blocks, items, dimension, position, lookup=None):
    block = blocks.GetBlockNew(position, dimension)
    if not block or block.get("name") == "minecraft:air":
        return ["No loaded block at %s." % (position,)]

    paired = blocks.GetChestPairedPosition(position, dimension)
    positions = (position, tuple(paired)) if paired is not None else (position,)
    lines = []
    for pos in positions:
        current = block if pos == position else blocks.GetBlockNew(pos, dimension)
        name = current.get("name") if current else None
        pair = paired if pos == position else blocks.GetChestPairedPosition(pos, dimension)
        size = items.GetContainerSize(pos, dimension)
        port = lookup(dimension, pos, "up", "item") if lookup is not None else None
        iml_slots = len(port.get_slots()) if port is not None else 0
        occupied = []
        if size in (27, 54):
            for slot in range(size):
                stack = items.GetContainerItem(pos, slot, dimension)
                if stack and stack.get("count"):
                    item = stack.get("newItemName") or stack.get("itemName")
                    occupied.append("%d=%s x%d" % (slot, item, stack["count"]))
        lines.append("pos=%s block=%s paired=%s size=%s iml_slots=%s %s"
                     % (pos, name, pair, size, iml_slots, ", ".join(occupied) or "no items read"))
    return lines
