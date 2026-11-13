import mod.server.extraServerApi as serverApi


ServerSystem = serverApi.GetServerSystemCls()
BATTERY = "iml_fe_receiver:battery"
CAPACITY_FE = 1000
LIMIT_FE = 200


class ReceiverSystem(ServerSystem):
    def __init__(self, namespace, system_name):
        ServerSystem.__init__(self, namespace, system_name)
        self._fe = None
        self._factory = serverApi.GetEngineCompFactory()
        self._game = self._factory.CreateGame(serverApi.GetLevelId())
        self._blocks = self._factory.CreateBlockInfo(serverApi.GetLevelId())
        self._engine_namespace = serverApi.GetEngineNamespace()
        self._engine_system = serverApi.GetEngineSystemName()
        self.ListenForEvent(self._engine_namespace, self._engine_system,
                            "ServerBlockUseEvent", self, self.on_use)
        self.ListenForEvent(self._engine_namespace, self._engine_system,
                            "ServerChatEvent", self, self.on_chat)
        self.ListenForEvent(self._engine_namespace, self._engine_system,
                            "LoadServerAddonScriptsAfter", self, self.register_ports)

    def register_ports(self, args):
        if self._fe is not None:
            return
        fe = serverApi.GetSystem("fe", "energy")
        if fe is not None:
            fe.register_block(BATTERY, self.battery_port)
            fe.register_block_capability(BATTERY, "item", self.item_port)
            self._fe = fe
            print("[FE receiver] Battery ports registered")

    def battery_port(self, dimension, position, face):
        if face == "up":
            return self._fe.create_block_storage(
                dimension, position, CAPACITY_FE, LIMIT_FE, 0
            )
        if face == "down":
            return self._fe.create_block_storage(
                dimension, position, CAPACITY_FE, 0, LIMIT_FE
            )
        return None

    def item_port(self, dimension, position, face):
        if face not in ("up", "down"):
            return None
        return self._fe.create_block_item_port(
            dimension, position, "iml_fe_receiver:items", {0: 8},
            lambda stack: 64, (0,) if face == "up" else (),
            (0,) if face == "down" else ())

    def on_chat(self, args):
        parts = args["message"].split()
        if parts[:1] == ["imlitem"]:
            args["cancel"] = True
            self.test_items(args["playerId"], parts[1:])
            return
        if parts[:2] != ["imlfe", "read"]:
            return
        args["cancel"] = True
        player = args["playerId"]
        try:
            if len(parts) != 5:
                raise ValueError()
            x, y, z = map(int, parts[2:])
        except ValueError:
            self.report(player, "Usage: imlfe read X Y Z")
            return
        self.interact(player, (x, y, z))

    def test_items(self, player, parts):
        if len(parts) != 4 or parts[0] not in ("probe", "read", "clear"):
            self.report(player, "Usage: imlitem probe|read|clear X Y Z")
            return
        try:
            position = tuple(map(int, parts[1:]))
        except ValueError:
            self.report(player, "[IML item] Invalid coordinates")
            return
        if self._fe is None:
            self.report(player, "[IML item] Library unavailable")
            return
        dimension = self._factory.CreateDimension(player).GetPlayerDimensionId()
        top = self._fe.get_block_capability(dimension, position, "up", "item")
        bottom = self._fe.get_block_capability(dimension, position, "down", "item")
        if top is None or bottom is None:
            self.report(player, "[IML item] No battery item port")
            return
        if parts[0] == "read":
            self.report(player, "[IML item] Stored: %r" % bottom.get_stack(0))
            return
        if parts[0] == "clear":
            self.report(player, "[IML item] Extracted: %r" % bottom.extract(0, 8))
            return
        if bottom.get_stack(0) is not None:
            self.report(player, "[IML item] Probe requires an empty battery")
            return
        stack = {"newItemName": "minecraft:apple", "count": 10,
                 "userData": {"imlProbe": "saved"}}
        expected = dict(stack, count=2)
        if (top.get_slot_key(0) != bottom.get_slot_key(0)
                or top.insert(0, stack, True) != expected
                or bottom.get_stack(0) is not None
                or bottom.insert(0, stack) != stack
                or top.insert(0, stack) != expected
                or top.extract(0, 1) is not None
                or bottom.get_stack(0) != dict(stack, count=8)):
            self.report(player, "[IML item] FAIL: slot or transfer mismatch")
            return
        self.report(player, "[IML item] PASS: 8 stored, 2 left over")

    def on_use(self, args):
        if args["blockName"] == "iml_fe_receiver:battery":
            self.interact(args["playerId"], (args["x"], args["y"], args["z"]))

    def report(self, player, message):
        print(message)
        self._game.SetOneTipMessage(player, message)

    def interact(self, player, position):
        dimension = self._factory.CreateDimension(player).GetPlayerDimensionId()
        block = self._blocks.GetBlockNew(position, dimension)
        if not block or block["name"] != "iml_fe_receiver:battery":
            self.report(player, "[FE] No battery at the given coordinates")
            return

        if self._fe is None:
            self.report(player, "[FE receiver] Battery ports unavailable")
            return
        port = self._fe.get_block_energy(dimension, position, "up")
        if port is None:
            self.report(player, "[FE receiver] Battery storage unavailable")
            return
        self.report(player, "[FE receiver] Battery %d/%d FE" % (
            port.get_energy_stored(), port.get_max_energy_stored()
        ))

    def Destroy(self):
        self.UnListenForEvent(self._engine_namespace, self._engine_system,
                              "ServerChatEvent", self, self.on_chat)
        self.UnListenForEvent(self._engine_namespace, self._engine_system,
                              "LoadServerAddonScriptsAfter", self, self.register_ports)
        self.UnListenForEvent(self._engine_namespace, self._engine_system,
                              "ServerBlockUseEvent", self, self.on_use)
