import mod.server.extraServerApi as serverApi


ServerSystem = serverApi.GetServerSystemCls()
PULSE_FE = 200


class SourceSystem(ServerSystem):
    def __init__(self, namespace, system_name):
        ServerSystem.__init__(self, namespace, system_name)
        self._factory = serverApi.GetEngineCompFactory()
        self._game = self._factory.CreateGame(serverApi.GetLevelId())
        self._blocks = self._factory.CreateBlockInfo(serverApi.GetLevelId())
        self._engine_namespace = serverApi.GetEngineNamespace()
        self._engine_system = serverApi.GetEngineSystemName()
        self.ListenForEvent(self._engine_namespace, self._engine_system,
                            "ServerBlockUseEvent", self, self.on_use)
        self.ListenForEvent(self._engine_namespace, self._engine_system,
                            "ServerChatEvent", self, self.on_chat)

    def on_chat(self, args):
        parts = args["message"].split()
        if parts[:2] != ["imlfe", "charge"]:
            return
        args["cancel"] = True
        player = args["playerId"]
        try:
            if len(parts) != 5:
                raise ValueError()
            x, y, z = map(int, parts[2:])
        except ValueError:
            self.report(player, "Usage: imlfe charge X Y Z")
            return
        self.interact(player, (x, y, z))

    def on_use(self, args):
        if args["blockName"] == "iml_fe_source:generator":
            self.interact(args["playerId"], (args["x"], args["y"], args["z"]))

    def report(self, player, message):
        print(message)
        self._game.SetOneTipMessage(player, message)

    def interact(self, player, position):
        dimension = self._factory.CreateDimension(player).GetPlayerDimensionId()
        block = self._blocks.GetBlockNew(position, dimension)
        if not block or block["name"] != "iml_fe_source:generator":
            self.report(player, "[FE] No generator at the given coordinates")
            return

        fe = serverApi.GetSystem("fe", "energy")
        if fe is None:
            self.report(player, "[FE source] FE system unavailable")
            return
        x, y, z = position
        port = fe.get_block_energy(dimension, (x, y - 1, z), "up")
        if port is None:
            self.report(player, "[FE source] No energy input below generator")
            return
        moved = port.receive_energy(PULSE_FE)
        self.report(player, "[FE source] Sent %d FE; target %d/%d FE" % (
            moved, port.get_energy_stored(), port.get_max_energy_stored()
        ))

    def Destroy(self):
        self.UnListenForEvent(self._engine_namespace, self._engine_system,
                              "ServerChatEvent", self, self.on_chat)
        self.UnListenForEvent(self._engine_namespace, self._engine_system,
                              "ServerBlockUseEvent", self, self.on_use)
