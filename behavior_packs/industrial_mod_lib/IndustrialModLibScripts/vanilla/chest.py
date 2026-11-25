from IndustrialModLibScripts.vanilla.container import ContainerItemPort


CHEST = "minecraft:chest"
CHEST_IDS = (CHEST, "minecraft:trapped_chest") + tuple(
    "minecraft:%s%scopper_chest" % (wax, oxidation)
    for wax in ("", "waxed_")
    for oxidation in ("", "exposed_", "weathered_", "oxidized_")
)


def _chest_layout(blocks, items, dimension, position):
    block = blocks.GetBlockNew(position, dimension)
    name = block.get("name") if block else None
    if name not in CHEST_IDS:
        return ()
    size = items.GetContainerSize(position, dimension)
    linked = blocks.GetChestPairedPosition(position, dimension)
    if linked is None:
        return ((position, name),) if size == 27 else ()
    other = tuple(linked)
    if (size != 54 or other[1] != position[1]
            or abs(other[0] - position[0]) + abs(other[2] - position[2]) != 1):
        return ()
    block = blocks.GetBlockNew(other, dimension)
    other_name = block.get("name") if block else None
    if other_name not in CHEST_IDS or items.GetContainerSize(other, dimension) != 54:
        return ()
    backlink = blocks.GetChestPairedPosition(other, dimension)
    if backlink is None or tuple(backlink) != position:
        return ()
    return tuple(sorted(((position, name), (other, other_name))))


def open_chest(blocks, items, dimension, position):
    position = tuple(position)
    layout = _chest_layout(blocks, items, dimension, position)
    if not layout:
        return None
    positions = tuple(pos for pos, _ in layout)

    def resolve_positions():
        if _chest_layout(blocks, items, dimension, position) == layout:
            return positions
        return ()

    # Keep the slot identity based on location even when a copper variant changes.
    return ContainerItemPort(items, dimension, CHEST, positions, resolve_positions)
