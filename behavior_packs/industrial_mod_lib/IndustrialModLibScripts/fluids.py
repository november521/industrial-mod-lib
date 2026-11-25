import re

from IndustrialModLibScripts.energy import INTEGER_TYPES


try:
    STRING_TYPES = (basestring,)
except NameError:
    STRING_TYPES = (str,)

FLUID_ID = re.compile(r"[a-z0-9_.-]+:[a-z0-9_./-]+\Z")


def _check_fluid_id(fluid_id):
    if not isinstance(fluid_id, STRING_TYPES):
        raise TypeError("Fluid IDs must be strings")
    if not FLUID_ID.match(fluid_id):
        raise ValueError("Fluid IDs must have a namespace and path")
    return fluid_id


def _check_amount(amount):
    if isinstance(amount, bool) or not isinstance(amount, INTEGER_TYPES):
        raise TypeError("Fluid amounts and capacities must be integers")
    if amount < 0:
        raise ValueError("Fluid amounts and capacities must be nonnegative")
    return amount


class FluidPort(object):
    """A face's view of a single-fluid tank. All amounts use integer mB."""

    def __init__(self, resolve_data, key, capacity, allowed_fluids=None,
                 can_fill=True, can_drain=True):
        self._resolve_data = resolve_data
        self._key = key
        self._capacity = _check_amount(capacity)
        self._allowed_fluids = None
        if allowed_fluids is not None:
            if isinstance(allowed_fluids, STRING_TYPES):
                raise TypeError("Allowed fluids must be an iterable of fluid IDs")
            self._allowed_fluids = frozenset(_check_fluid_id(fluid_id)
                                             for fluid_id in allowed_fluids)
        self._can_fill = can_fill
        self._can_drain = can_drain

    def get_capacity(self):
        return self._capacity

    def get_fluid(self):
        """Return (fluid_id, amount), or None for an empty or unavailable tank."""
        data = self._resolve_data()
        return self._read(data) if data is not None else None

    def fill(self, fluid_id, amount, simulate=False):
        _check_fluid_id(fluid_id)
        _check_amount(amount)
        if not self._can_fill or not amount:
            return 0
        if self._allowed_fluids is not None and fluid_id not in self._allowed_fluids:
            return 0
        data = self._resolve_data()
        if data is None:
            return 0
        current = self._read(data)
        if current is not None and current[0] != fluid_id:
            return 0
        stored = current[1] if current is not None else 0
        filled = min(amount, max(0, self._capacity - stored))
        if filled and not simulate:
            data[self._key] = {"fluid_id": fluid_id, "amount": stored + filled}
        return filled

    def drain(self, fluid_id, amount, simulate=False):
        _check_fluid_id(fluid_id)
        _check_amount(amount)
        if not self._can_drain or not amount:
            return 0
        data = self._resolve_data()
        if data is None:
            return 0
        current = self._read(data)
        if current is None or current[0] != fluid_id:
            return 0
        stored = current[1]
        drained = min(amount, stored)
        if not simulate:
            remaining = stored - drained
            data[self._key] = {"fluid_id": fluid_id, "amount": remaining} if remaining else {}
        return drained

    def _read(self, data):
        try:
            record = data[self._key]
        except KeyError:
            return None
        if not record:
            return None
        amount = _check_amount(record["amount"])
        return (_check_fluid_id(record["fluid_id"]), amount) if amount else None
