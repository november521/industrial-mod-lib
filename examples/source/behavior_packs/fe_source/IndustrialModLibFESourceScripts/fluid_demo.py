from IndustrialModLibFESourceScripts.fluid_transport import move_fluid


TANK = "iml_fe_receiver:tank"
FLUID_NAMES = {"minecraft:water": "Water", "minecraft:lava": "Lava"}
FLUIDS = tuple(FLUID_NAMES)
GENERATOR_CAPACITY = 1500
STORAGE_KEY = "iml_fe_source:fluid"
RECOVERY_KEY = "iml_fe_source:fluid_recovery"


def describe_fluid(port):
    if port is None:
        return "Unavailable"
    capacity = port.get_capacity()
    contents = port.get_fluid()
    if contents is None:
        return "Empty (0/%d mB)" % capacity
    fluid, amount = contents
    return "%s %d/%d mB" % (FLUID_NAMES.get(fluid, fluid), amount, capacity)


def run_fluid_demo(library, dimension, position, is_tank, action):
    x, y, z = position
    below = (x, y - 1, z)
    source = library.get_block_capability(dimension, position, "down", "fluid")
    if source is None:
        return "Fluid output unavailable."
    if is_tank:
        label = "Tank"
        restore = library.get_block_capability(dimension, position, "up", "fluid")
        if action in ("seed", "partial"):
            return "Load samples at the generator."
    else:
        label = "Generator"
        restore = library.create_block_fluid_port(
            dimension, position, STORAGE_KEY, GENERATOR_CAPACITY, allowed_fluids=FLUIDS)
    if restore is None:
        return "Fluid storage unavailable."

    target = library.get_block_capability(dimension, below, "up", "fluid")
    recovery = library.create_block_fluid_port(
        dimension, position, RECOVERY_KEY, source.get_capacity(), allowed_fluids=FLUIDS)
    summary = "Fluid inventory"
    if action in ("seed", "partial"):
        if source.get_fluid() is not None:
            return "Send the remaining fluid before loading another sample."
        fluid = "minecraft:water" if action == "seed" else "minecraft:lava"
        amount = restore.fill(fluid, GENERATOR_CAPACITY)
        summary = "Loaded %d mB of %s" % (amount, FLUID_NAMES[fluid])
    elif action in ("preview", "send"):
        if target is None:
            summary = "Place a tank directly below."
        elif action == "send" and recovery is None:
            summary = "Recovery storage unavailable."
        else:
            planned, moved, _, _ = move_fluid(
                source, target, recovery, simulate=action == "preview", restore=restore)
            summary = ("Preview: %d mB" % planned if action == "preview"
                       else "Moved: %d / %d mB" % (moved, planned))

    return "%s\n%s: %s\nTank below: %s\nRecovery: %s" % (
        summary, label, describe_fluid(source), describe_fluid(target),
        describe_fluid(recovery))
