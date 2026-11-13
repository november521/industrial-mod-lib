class CapabilityRegistry(object):
    def __init__(self):
        self._providers = {}

    def register(self, identifier, capability, provider):
        if not callable(provider):
            raise TypeError("Capability provider must be callable")
        key = (identifier, capability)
        if key in self._providers:
            raise ValueError("Capability provider already registered: %r" % (key,))
        self._providers[key] = provider

    def get(self, identifier, capability):
        return self._providers.get((identifier, capability))
