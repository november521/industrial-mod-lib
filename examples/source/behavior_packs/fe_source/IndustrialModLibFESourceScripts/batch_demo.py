from IndustrialModLibFESourceScripts.item_batch import run_item_batch, run_item_gather


CONDUIT = "iml_fe_receiver:item_conduit"
RECOVERY_KEY = "iml_fe_receiver:conduit_recovery"
ITEM_BUDGET = 10
SCAN_BUDGET = 8


def conduit_recovery(library, dimension, position):
    return library.create_block_item_port(
        dimension, position, RECOVERY_KEY, {0: 16}, None, (0,), (0,))


def run_batch_demo(library, blocks, dimension, position, storage, sample, action):
    x, y, z = position
    conduit = (x, y - 1, z)
    block = blocks.GetBlockNew(conduit, dimension)
    if not block or block["name"] != CONDUIT:
        return "Place an Item Conduit below the generator."
    source = library.get_block_capability(dimension, position, "down", "item")
    if source is None or storage is None:
        return "Generator inventory unavailable."
    recovery = conduit_recovery(library, dimension, conduit)
    if recovery is None:
        return "Conduit recovery unavailable."

    targets = (
        library.get_block_capability(dimension, (x, y - 2, z), "up", "item"),
        library.get_block_capability(dimension, (x + 1, y - 1, z), "west", "item"),
    )
    if action == "seed":
        if source.get_stack(0) is not None:
            return "Seed requires an empty generator."
        storage.insert(0, sample)

    result_lines = []
    if action in ("preview", "send"):
        preview = action == "preview"
        result = run_item_batch(source, storage, recovery, targets,
                                simulate=preview, max_items=ITEM_BUDGET, max_slots=SCAN_BUDGET)
        for index, label in enumerate(("Down", "East")):
            if targets[index] is None:
                result_lines.append("%s: Disconnected" % label)
            elif preview:
                result_lines.append("%s: %d planned" % (label, result["planned"][index]))
            else:
                result_lines.append("%s: %d moved / %d planned" % (
                    label, result["moved"][index], result["planned"][index]))
        result_lines.append("Scanned: %d/%d slots" % (result["scanned"], SCAN_BUDGET))
        if result["restored"]:
            result_lines.append("Returned: %d" % result["restored"])
    else:
        for target, label in zip(targets, ("Down", "East")):
            result_lines.append("%s: %s" % (label, "Connected" if target is not None else "Disconnected"))
    source_stack = source.get_stack(0)
    recovered_stack = recovery.get_stack(0)
    result_lines.append("Generator: %d   Recovery: %d" % (
        source_stack["count"] if source_stack else 0,
        recovered_stack["count"] if recovered_stack else 0))
    return "\n".join(result_lines)


def _gather_port(library, dimension, position, face):
    port = library.get_block_capability(dimension, position, face, "item")
    return port if port is not None and port.get_slots() else None


def run_gather_demo(library, blocks, dimension, position, action):
    x, y, z = position
    below = (x, y - 1, z)
    target = _gather_port(library, dimension, below, "up")
    if target is None:
        return "Connect an item input below the Item Conduit."
    recovery = conduit_recovery(library, dimension, position)
    if recovery is None:
        return "Conduit recovery unavailable."
    sources = (
        _gather_port(library, dimension, (x - 1, y, z), "east"),
        _gather_port(library, dimension, (x + 1, y, z), "west"),
    )

    result = None
    if action in ("preview", "send"):
        result = run_item_gather(sources, target, recovery,
                                 simulate=action == "preview", max_items=ITEM_BUDGET)
    lines = []
    for index, label in enumerate(("West", "East")):
        if sources[index] is None:
            lines.append("%s: Disconnected" % label)
        elif action == "preview":
            lines.append("%s: %d planned" % (label, result["planned"][index]))
        elif action == "send":
            lines.append("%s: %d moved / %d planned" % (
                label, result["moved"][index], result["planned"][index]))
        else:
            stack = sources[index].get_stack(sources[index].get_slots()[0])
            lines.append("%s: %d in first slot" % (label, stack["count"] if stack else 0))

    stored = target.get_stack(target.get_slots()[0])
    buffered = recovery.get_stack(0)
    block = blocks.GetBlockNew(below, dimension)
    label = "Battery" if block and block["name"] == "iml_fe_receiver:battery" else "Output"
    lines.append("%s: %d   Recovery: %d" % (label,
        stored["count"] if stored else 0, buffered["count"] if buffered else 0))
    if result and result["recovery_blocked"]:
        lines.append("Recovery has insufficient space.")
    if result and result["returned"]:
        lines.append("Returned: %d" % result["returned"])
    return "\n".join(lines)
