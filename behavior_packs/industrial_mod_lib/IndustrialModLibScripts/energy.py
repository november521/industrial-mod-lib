try:
    INTEGER_TYPES = (int, long)
except NameError:
    INTEGER_TYPES = (int,)


def nonnegative_integer(value):
    if isinstance(value, bool) or not isinstance(value, INTEGER_TYPES):
        raise TypeError("FE amounts must be integers")
    if value < 0:
        raise ValueError("FE amounts must be nonnegative")
    return value


class EnergyStorage(object):
    """An energy port backed by a dict-like store, optionally persistent."""

    def __init__(self, capacity, max_receive, max_extract, data=None,
                 key="fe:energy"):
        self._capacity = nonnegative_integer(capacity)
        self._max_receive = nonnegative_integer(max_receive)
        self._max_extract = nonnegative_integer(max_extract)
        self._data = {} if data is None else data
        self._key = key

    def get_energy_stored(self):
        try:
            value = self._data[self._key]
        except KeyError:
            return 0
        if value is None:
            return 0
        return min(self._capacity, nonnegative_integer(value))

    def get_max_energy_stored(self):
        return self._capacity

    def can_receive(self):
        return self._max_receive > 0

    def can_extract(self):
        return self._max_extract > 0

    def receive_energy(self, amount, simulate=False):
        amount = nonnegative_integer(amount)
        stored = self.get_energy_stored()
        accepted = min(amount, self._max_receive, self._capacity - stored)
        if accepted and not simulate:
            self._data[self._key] = stored + accepted
        return accepted

    def extract_energy(self, amount, simulate=False):
        amount = nonnegative_integer(amount)
        stored = self.get_energy_stored()
        extracted = min(amount, self._max_extract, stored)
        if extracted and not simulate:
            self._data[self._key] = stored - extracted
        return extracted
