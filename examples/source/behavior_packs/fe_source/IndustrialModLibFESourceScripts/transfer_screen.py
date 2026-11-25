import mod.client.extraClientApi as clientApi

from IndustrialModLibFESourceScripts.client import NAMESPACE


ScreenNode = clientApi.GetScreenNodeCls()
ViewBinder = clientApi.GetViewBinderCls()


class TransferScreen(ScreenNode):
    def __init__(self, namespace, name, params):
        ScreenNode.__init__(self, namespace, name, params)
        self.mode = (params or {}).get("mode", "item_source")

    def Create(self):
        self.client = clientApi.GetSystem(NAMESPACE, "client")
        self.client.panel = self
        self.result = self.GetBaseUIControl("/panel/result").asLabel()
        for name, callback in (
                ("seed", self.seed), ("refresh", self.refresh),
                ("send", self.send), ("partial", self.partial), ("preview", self.preview),
                ("pull", self.pull), ("close", self.close)):
            button = self.GetBaseUIControl("/panel/" + name).asButton()
            button.AddTouchEventParams({"isSwallow": True})
            button.SetButtonTouchUpCallback(callback)
        self.GetBaseUIControl("/panel/pull").SetVisible(self.mode == "battery")
        title = self.GetBaseUIControl("/panel/title").asLabel()
        if self.mode == "battery":
            title.SetText("Battery Inventory")
            for name in ("seed", "send", "partial"):
                self.GetBaseUIControl("/panel/" + name).SetVisible(False)
        elif self.mode == "fluid_source":
            title.SetText("Generator Fluids")
            self.GetBaseUIControl("/panel/seed/label").asLabel().SetText("Load Water")
            self.GetBaseUIControl("/panel/partial/label").asLabel().SetText("Load Lava")
        elif self.mode in ("batch", "gather"):
            title.SetText("Item Gathering" if self.mode == "gather" else "Batch Item Transfer")
            self.GetBaseUIControl("/panel/send/label").asLabel().SetText("Run Round")
            self.GetBaseUIControl("/panel/partial").SetVisible(False)
            self.GetBaseUIControl("/panel/seed").SetVisible(self.mode == "batch")
        elif self.mode == "tank":
            title.SetText("Fluid Tank")
            self.GetBaseUIControl("/panel/send/label").asLabel().SetText("Send Down")
            for name in ("seed", "partial"):
                self.GetBaseUIControl("/panel/" + name).SetVisible(False)
        self.refresh(None)

    def show_result(self, text):
        self.result.SetText(text)

    def request(self, action):
        self.client.NotifyToServer("TransferAction", {"action": action})

    def seed(self, args):
        self.request("seed")

    def refresh(self, args):
        self.request("source")

    def send(self, args):
        self.request("send")

    def partial(self, args):
        self.request("partial")

    def preview(self, args):
        self.request("preview")

    def pull(self, args):
        self.request("pull")

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp, "#iml_transfer_close")
    def close(self, args):
        clientApi.PopScreen()

    def Destroy(self):
        if self.client.panel is self:
            self.client.panel = None
