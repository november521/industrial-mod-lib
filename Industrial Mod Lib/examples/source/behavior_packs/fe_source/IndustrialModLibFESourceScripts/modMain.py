from mod.common.mod import Mod
import mod.server.extraServerApi as serverApi


@Mod.Binding(name="IndustrialModLibFESource", version="0.1.0")
class SourceDemo(object):
    @Mod.InitServer()
    def init_server(self):
        serverApi.RegisterSystem(
            "iml_fe_source", "server",
            "IndustrialModLibFESourceScripts.server.SourceSystem"
        )
