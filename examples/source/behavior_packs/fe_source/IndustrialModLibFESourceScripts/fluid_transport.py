def move_fluid(source, target, recovery, simulate=False, restore=None):
    """Return planned, delivered, restored, and buffered amounts in mB."""
    current = source.get_fluid()
    if current is None:
        return 0, 0, 0, 0

    fluid_id, amount = current
    offered = source.drain(fluid_id, amount, simulate=True)
    planned = target.fill(fluid_id, offered, simulate=True) if offered else 0
    if simulate or not planned:
        return planned, 0, 0, 0

    # These ports operate synchronously. Ensure the entire drain has a
    # compatible fallback before changing any inventory.
    if recovery is None or recovery.fill(fluid_id, planned, simulate=True) != planned:
        return planned, 0, 0, 0
    removed = source.drain(fluid_id, planned)
    if not removed:
        return planned, 0, 0, 0

    delivered = target.fill(fluid_id, removed)
    rejected = removed - delivered
    if not rejected:
        return planned, delivered, 0, 0

    undo = source if restore is None else restore
    restored = undo.fill(fluid_id, rejected)
    remainder = rejected - restored
    buffered = recovery.fill(fluid_id, remainder) if remainder else 0
    if buffered != remainder:
        raise RuntimeError("Recovery lost capacity for %d mB of %s"
                           % (remainder - buffered, fluid_id))
    return planned, delivered, restored, buffered
