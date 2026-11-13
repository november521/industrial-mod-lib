from mod.common.mod import Mod
import mod.server.extraServerApi as serverApi


@Mod.Binding(name="FE", version="0.1.0")
class FE(object):
    @Mod.InitServer()
    def init_server(self):
        serverApi.RegisterSystem(
            "fe", "energy", "IndustrialModLibScripts.server.EnergySystem"
        )
