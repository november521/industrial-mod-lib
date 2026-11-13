from copy import deepcopy

from IndustrialModLibScripts.energy import INTEGER_TYPES


class ItemPort(object):
    """A face's view of a dict-like inventory, with string keys for persistence."""

    def __init__(self, resolve_data, inventory_key, slot_limits, item_limit,
                 insert_slots, extract_slots, storage_prefix=""):
        self._resolve_data = resolve_data
        self._inventory_key = inventory_key
        self._limits = {self._count(slot): self._count(limit)
                        for slot, limit in slot_limits.items()}
        self._storage_prefix = storage_prefix
        self._item_limit = item_limit
        self._insert_slots = frozenset(insert_slots)
        self._extract_slots = frozenset(extract_slots)
        if not (self._insert_slots | self._extract_slots) <= set(self._limits):
            raise ValueError("Access configured for an unknown slot")

    def get_slots(self):
        return tuple(sorted(self._limits))

    def get_slot_key(self, slot):
        self._limits[slot]
        return (self._inventory_key, slot)

    def get_slot_limit(self, slot):
        return self._limits[slot]

    def get_stack(self, slot):
        self._limits[slot]
        return deepcopy(self._read(self._resolve_data(), slot))

    def insert(self, slot, stack, simulate=False):
        limit = self.get_slot_limit(slot)
        if stack is None or self._count(stack["count"]) == 0:
            return None
        remainder = deepcopy(stack)
        data = self._resolve_data()
        if data is None or slot not in self._insert_slots:
            return remainder
        current = self._read(data, slot)
        item_limit = self._count(self._item_limit(deepcopy(stack)))
        stored = 0
        if current is not None:
            stored = current["count"]
            identity = dict(current)
            del identity["count"]
            incoming = dict(stack)
            del incoming["count"]
            if identity != incoming:
                return remainder
        accepted = min(stack["count"], max(0, min(limit, item_limit) - stored))
        if accepted and not simulate:
            updated = deepcopy(stack)
            updated["count"] = stored + accepted
            data[self._storage_prefix + str(slot)] = updated
        remainder["count"] -= accepted
        return remainder if remainder["count"] else None

    def extract(self, slot, count, simulate=False):
        self._limits[slot]
        count = self._count(count)
        data = self._resolve_data()
        if data is None or slot not in self._extract_slots or not count:
            return None
        current = self._read(data, slot)
        if current is None:
            return None
        extracted = deepcopy(current)
        extracted["count"] = min(count, current["count"],
                                 self._count(self._item_limit(deepcopy(current))))
        if not extracted["count"]:
            return None
        if not simulate:
            remaining = deepcopy(current)
            remaining["count"] -= extracted["count"]
            data[self._storage_prefix + str(slot)] = (
                remaining if remaining["count"] else {})
        return extracted

    def _read(self, data, slot):
        if data is not None:
            try:
                return data[self._storage_prefix + str(slot)] or None
            except KeyError:
                pass
        return None

    @staticmethod
    def _count(value):
        if isinstance(value, bool) or not isinstance(value, INTEGER_TYPES):
            raise TypeError("Item counts and limits must be integers")
        if value < 0:
            raise ValueError("Item counts and limits must be nonnegative")
        return value
