import mod.client.extraClientApi as clientApi

from IndustrialModLibFESourceScripts.client import NAMESPACE


ScreenNode = clientApi.GetScreenNodeCls()
ViewBinder = clientApi.GetViewBinderCls()


class TransferScreen(ScreenNode):
    def __init__(self, namespace, name, params):
        ScreenNode.__init__(self, namespace, name, params)
        self.battery = (params or {}).get("battery", False)

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
        self.GetBaseUIControl("/panel/pull").SetVisible(self.battery)
        if self.battery:
            self.GetBaseUIControl("/panel/title").asLabel().SetText("Battery Inventory")
            for name in ("seed", "send", "partial"):
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
