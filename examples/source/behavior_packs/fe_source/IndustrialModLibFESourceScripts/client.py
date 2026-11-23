import mod.client.extraClientApi as clientApi


NAMESPACE = "iml_fe_source"
UI_KEY = "transfer_panel"
ClientSystem = clientApi.GetClientSystemCls()


class TransferClient(ClientSystem):
    def __init__(self, namespace, name):
        ClientSystem.__init__(self, namespace, name)
        self.panel = None
        self.ready = False
        self.engine = (clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName())
        factory = clientApi.GetEngineCompFactory()
        self.camera = factory.CreateCamera(clientApi.GetLevelId())
        self.blocks = factory.CreateBlockInfo(clientApi.GetLevelId())
        self.ListenForEvent(self.engine[0], self.engine[1], "RightClickBeforeClientEvent",
                            self, self.on_right_click)
        self.ListenForEvent(self.engine[0], self.engine[1], "UiInitFinished", self, self.register)
        self.ListenForEvent(NAMESPACE, "server", "OpenTransferPanel", self, self.open_panel)
        self.ListenForEvent(NAMESPACE, "server", "TransferResult", self, self.show_result)

    def register(self, args):
        self.ready = clientApi.RegisterUI(
            NAMESPACE, UI_KEY,
            "IndustrialModLibFESourceScripts.transfer_screen.TransferScreen",
            "iml_transfer.main")

    def open_panel(self, args):
        if self.ready and self.panel is None:
            clientApi.PushScreen(NAMESPACE, UI_KEY, {"battery": args.get("battery", False)})

    def on_right_click(self, args):
        if not self.ready or self.panel is not None:
            return
        factory = clientApi.GetEngineCompFactory()
        player_id = clientApi.GetLocalPlayerId()
        player = factory.CreatePlayer(player_id)
        if player.isSneaking() and factory.CreateItem(player_id).GetCarriedItem():
            return
        hit = self.camera.PickFacing()
        if not hit or hit.get("type") != "Block":
            return
        position = (hit["x"], hit["y"], hit["z"])
        block = self.blocks.GetBlock(position)
        if block and block[0] in ("iml_fe_source:generator", "iml_fe_receiver:battery"):
            args["cancel"] = True
            self.NotifyToServer("TransferAction", {"action": "open", "position": list(position)})

    def show_result(self, args):
        if self.panel is not None:
            self.panel.show_result(args["text"])

    def Destroy(self):
        self.UnListenForEvent(self.engine[0], self.engine[1], "RightClickBeforeClientEvent",
                              self, self.on_right_click)
        self.UnListenForEvent(self.engine[0], self.engine[1], "UiInitFinished", self, self.register)
        self.UnListenForEvent(NAMESPACE, "server", "OpenTransferPanel", self, self.open_panel)
        self.UnListenForEvent(NAMESPACE, "server", "TransferResult", self, self.show_result)
