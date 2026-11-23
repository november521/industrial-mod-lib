def plan_one_slot(source, target, source_slot=0, target_slot=0):
    offered = source.extract(source_slot, 10, True)
    if offered is None:
        return 0
    remainder = target.insert(target_slot, offered, True)
    return offered["count"] - (remainder["count"] if remainder else 0)


def move_one_slot(source, target, restore, source_slot=0, target_slot=0):
    """Return the planned count, delivered count, and remainder to buffer."""
    planned = plan_one_slot(source, target, source_slot, target_slot)
    if not planned:
        return 0, 0, None
    extracted = source.extract(source_slot, planned)
    if extracted is None:
        return planned, 0, None
    remainder = target.insert(target_slot, extracted)
    if remainder is None:
        return planned, extracted["count"], None
    delivered = extracted["count"] - remainder["count"]
    return planned, delivered, restore.insert(source_slot, remainder)
