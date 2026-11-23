import mod.server.extraServerApi as serverApi

from IndustrialModLibScripts.capabilities.registry import CapabilityRegistry
from IndustrialModLibScripts.energy import EnergyStorage
from IndustrialModLibScripts.items import ItemPort
from IndustrialModLibScripts.vanilla.chest import CHEST, open_chest


ServerSystem = serverApi.GetServerSystemCls()
FACES = ("down", "up", "north", "south", "west", "east")


class EnergySystem(ServerSystem):
    api_version = 1

    def __init__(self, namespace, system_name):
        ServerSystem.__init__(self, namespace, system_name)
        self._registry = CapabilityRegistry()
        factory = serverApi.GetEngineCompFactory()
        level_id = serverApi.GetLevelId()
        self._block_info = factory.CreateBlockInfo(level_id)
        self._block_entities = factory.CreateBlockEntityData(level_id)
        self._items = factory.CreateItem(level_id)
        self.register_block_capability(CHEST, "item", self._chest_port)

    def _chest_port(self, dimension, position, face):
        return open_chest(self._block_info, self._items, dimension, position)

    def register_block(self, identifier, provider):
        """Register a callable taking (dimension, position, face)."""
        self.register_block_capability(identifier, "energy", provider)

    def register_block_capability(self, identifier, capability, provider):
        self._registry.register(identifier, capability, provider)

    def get_block_energy(self, dimension, position, face):
        """Resolve the current port at a block face, or return None."""
        return self.get_block_capability(dimension, position, face, "energy")

    def get_block_capability(self, dimension, position, face, capability):
        if face not in FACES:
            raise ValueError("Unknown block face: " + str(face))
        block = self._block_info.GetBlockNew(position, dimension)
        if not block:
            return None
        provider = self._registry.get(block["name"], capability)
        if provider is None:
            return None
        return provider(dimension, position, face)

    def create_storage(self, capacity, max_receive, max_extract, data=None,
                       key="fe:energy"):
        return EnergyStorage(capacity, max_receive, max_extract, data, key)

    def create_block_storage(self, dimension, position, capacity,
                             max_receive, max_extract, key="fe:energy"):
        """Resolve persistent storage for a loaded custom block entity."""
        data = self._block_entities.GetBlockEntityData(dimension, position)
        if data is None:
            return None
        return EnergyStorage(capacity, max_receive, max_extract, data, key)

    def create_block_item_port(self, dimension, position, key, slot_limits,
                               item_limit, insert_slots, extract_slots):
        """Build a face view over the current custom block entity."""
        position = tuple(position)
        state = self._block_info.GetBlockNew(position, dimension)
        if not state:
            return None
        state = dict(state)

        def resolve_data():
            if self._block_info.GetBlockNew(position, dimension) != state:
                return None
            return self._block_entities.GetBlockEntityData(dimension, position)

        if resolve_data() is None:
            return None
        return ItemPort(resolve_data, (dimension, position, key), slot_limits,
                        item_limit, insert_slots, extract_slots, key + ":")
