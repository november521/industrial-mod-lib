from mod.common.mod import Mod
import mod.server.extraServerApi as serverApi


@Mod.Binding(name="IndustrialModLibFEReceiver", version="0.1.0")
class ReceiverDemo(object):
    @Mod.InitServer()
    def init_server(self):
        serverApi.RegisterSystem(
            "iml_fe_receiver", "server",
            "IndustrialModLibFEReceiverScripts.server.ReceiverSystem"
        )
