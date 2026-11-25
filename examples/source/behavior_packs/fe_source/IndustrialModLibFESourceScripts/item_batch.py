from copy import deepcopy


def _count(stack):
    return stack["count"] if stack else 0


def _offer(port, slot, stack, count, simulate=False):
    offered = deepcopy(stack)
    offered["count"] = count
    return count - _count(port.insert(slot, offered, simulate=simulate))


def _plan_targets(stack, source_key, targets, max_slots):
    allocations = []
    allocated = set()
    remaining = stack["count"]
    scanned = 0
    for index, target in enumerate(targets):
        if target is None:
            continue
        for slot in target.get_slots():
            scanned += 1
            key = target.get_slot_key(slot)
            if key != source_key and key not in allocated:
                accepted = _offer(target, slot, stack, remaining, simulate=True)
                if accepted:
                    allocations.append((index, slot, accepted))
                    allocated.add(key)
                    remaining -= accepted
            if not remaining or scanned == max_slots:
                return allocations, scanned
    return allocations, scanned


def run_item_batch(source, restore, recovery, targets, simulate=False,
                   max_items=10, max_slots=8):
    """Plan or execute one ordered round from source slot 0.

    The restore port writes back to the source's physical slot 0. Recovery
    uses slot 0 of a dedicated inventory. Execution assumes these synchronous
    ports honor simulated capacity and report their actual writes accurately.
    """
    planned = [0] * len(targets)
    moved = list(planned)
    result = {"planned": tuple(planned), "moved": tuple(moved), "scanned": 0,
              "restored": 0, "buffered": 0}
    if max_items <= 0 or max_slots <= 0:
        return result
    stack = source.extract(0, max_items, simulate=True)
    if not stack:
        return result

    allocations, result["scanned"] = _plan_targets(
        stack, source.get_slot_key(0), targets, max_slots)
    for index, slot, count in allocations:
        planned[index] += count
    result["planned"] = tuple(planned)
    total = sum(planned)
    if simulate or not total:
        return result

    # Reserve room for a round in which every destination rejects its offer.
    if recovery is None or _offer(recovery, 0, stack, total, simulate=True) != total:
        return result
    extracted = source.extract(0, total)
    available = _count(extracted)
    for index, slot, count in allocations:
        if not available:
            break
        offered = min(count, available)
        moved[index] += _offer(targets[index], slot, extracted, offered)
        available -= offered
    result["moved"] = tuple(moved)

    rejected = _count(extracted) - sum(moved)
    if rejected:
        result["restored"] = _offer(restore, 0, extracted, rejected)
        remainder = rejected - result["restored"]
        if remainder:
            result["buffered"] = _offer(recovery, 0, extracted, remainder)
            if result["buffered"] != remainder:
                raise RuntimeError("Item recovery lost capacity for %d item(s)"
                                   % (remainder - result["buffered"]))
    return result


def _plan_sources(sources, target, target_slot, max_items):
    allocations = []
    seen = {target.get_slot_key(target_slot)}
    reserved = 0
    reserved_stack = None
    for index, source in enumerate(sources):
        if source is None:
            continue
        source_slot = source.get_slots()[0]
        key = source.get_slot_key(source_slot)
        if key in seen:
            continue
        stack = source.extract(source_slot, max_items - reserved, simulate=True)
        if not stack:
            continue
        seen.add(key)
        if reserved_stack is not None and dict(stack, count=0) != reserved_stack:
            continue

        # Simulate the combined offer against the unchanged destination slot.
        accepted = _offer(target, target_slot, stack, reserved + stack["count"], simulate=True)
        if accepted > reserved:
            allocations.append((index, source_slot, stack, accepted - reserved))
            reserved = accepted
            reserved_stack = dict(stack, count=0)
            if reserved == max_items:
                break
    return allocations


def run_item_gather(sources, target, recovery, simulate=False, max_items=10):
    """Combine supplies into the target port's first slot in source order.

    Each source uses its first slot for extraction and for returning rejected items.
    """
    target_slot = target.get_slots()[0]
    allocations = _plan_sources(sources, target, target_slot, max_items)
    planned = [0] * len(sources)
    moved = list(planned)
    returned = 0
    recovery_blocked = False
    for index, source_slot, stack, count in allocations:
        planned[index] = count
        if simulate:
            continue
        if recovery is None or _offer(recovery, 0, stack, count, simulate=True) != count:
            recovery_blocked = True
            continue

        source = sources[index]
        extracted = source.extract(source_slot, count)
        if not extracted:
            continue
        moved[index] = _offer(target, target_slot, extracted, extracted["count"])
        rejected = extracted["count"] - moved[index]
        if rejected:
            restored = _offer(source, source_slot, extracted, rejected)
            returned += restored
            remainder = rejected - restored
            if remainder and _offer(recovery, 0, extracted, remainder) != remainder:
                raise RuntimeError("Conduit recovery rejected the unsent stack")
    return {
        "planned": tuple(planned), "moved": tuple(moved), "returned": returned,
        "recovery_blocked": recovery_blocked,
    }
