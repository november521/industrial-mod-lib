import mod.server.extraServerApi as serverApi
from IndustrialModLibFESourceScripts.batch_demo import CONDUIT, run_batch_demo, run_gather_demo
from IndustrialModLibFESourceScripts.chest_probe import describe_chest
from IndustrialModLibFESourceScripts.fluid_demo import (
    FLUIDS, GENERATOR_CAPACITY, STORAGE_KEY, TANK, run_fluid_demo)
from IndustrialModLibFESourceScripts.transport import move_one_slot, plan_one_slot


ServerSystem = serverApi.GetServerSystemCls()
PULSE_FE = 200
GENERATOR = "iml_fe_source:generator"
BATTERY = "iml_fe_receiver:battery"
PARTIAL_ITEM_TEST = "iml_fe_receiver:partial_item_test"
ITEM_KEY = "iml_fe_source:items"
SAMPLE_ID = "iml:transfer_sample"
SAMPLE_STACK = {
    "newItemName": "minecraft:apple", "count": 10,
    "extraId": SAMPLE_ID, "customTips": "IML Transfer Sample",
}


class SourceSystem(ServerSystem):
    def __init__(self, namespace, system_name):
        ServerSystem.__init__(self, namespace, system_name)
        self._factory = serverApi.GetEngineCompFactory()
        self._game = self._factory.CreateGame(serverApi.GetLevelId())
        self._blocks = self._factory.CreateBlockInfo(serverApi.GetLevelId())
        self._fe = None
        self._panel_targets = {}
        self.ListenForEvent("iml_fe_source", "client", "TransferAction",
                            self, self.on_transfer_action)
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
            fe.register_block_capability(GENERATOR, "item", self.item_port)
            fe.register_block_capability(GENERATOR, "fluid", self.fluid_port)
            self._fe = fe

    def item_port(self, dimension, position, face):
        if face != "down":
            return None
        return self._fe.create_block_item_port(
            dimension, position, ITEM_KEY, {0: 16}, lambda stack: 64, (), (0,))

    def storage_port(self, dimension, position):
        return self._fe.create_block_item_port(
            dimension, position, ITEM_KEY, {0: 16, 1: 16},
            lambda stack: 64, (0, 1), ())

    def fluid_port(self, dimension, position, face):
        if face != "down":
            return None
        return self._fe.create_block_fluid_port(
            dimension, position, STORAGE_KEY, GENERATOR_CAPACITY,
            allowed_fluids=FLUIDS, can_fill=False)

    def transfer_target(self, dimension, position, capability):
        x, y, z = position
        below = (x, y - 1, z)
        port = self._fe.get_block_capability(dimension, below, "up", capability)
        if port is None and capability == "item":
            # A side route leaves a vanilla container's lid clear.
            east = self._fe.get_block_capability(dimension, (x + 1, y, z), "west", capability)
            return "Target", east
        block = self._blocks.GetBlockNew(below, dimension)
        return ("Battery" if block and block.get("name") == BATTERY else "Target"), port

    def test_stock(self, player, parts, report=None):
        report = self.report if report is None else report
        try:
            if len(parts) != 4 and not (len(parts) == 5 and parts[0] in ("preview", "send")):
                raise ValueError()
            position = tuple(map(int, parts[1:4]))
            target_slot = int(parts[4]) if len(parts) == 5 else None
        except ValueError:
            report(player, "Usage: imlmove seed|source|preview|send|partial X Y Z [slot]")
            return
        if self._fe is None:
            report(player, "[IML source] Library unavailable")
            return
        dimension = self._factory.CreateDimension(player).GetPlayerDimensionId()
        block = self._blocks.GetBlockNew(position, dimension)
        if not block or block["name"] != GENERATOR:
            report(player, "[IML source] No generator at these coordinates")
            return
        source = self._fe.get_block_capability(dimension, position, "down", "item")
        if source is None:
            report(player, "[IML source] No generator item port")
            return
        storage = self.storage_port(dimension, position)
        if storage is None:
            report(player, "[IML source] Storage unavailable")
            return
        if parts[0] in ("send", "partial", "preview"):
            capability = PARTIAL_ITEM_TEST if parts[0] == "partial" else "item"
            target_label, target = self.transfer_target(dimension, position, capability)
            if target is None:
                message = ("Place the matching test battery below the generator."
                           if parts[0] == "partial" else "No item input below or to the east.")
                report(player, message)
                return
            slots = target.get_slots()
            if target_slot is None and slots:
                target_slot = slots[0]
            if target_slot not in slots:
                report(player, "Target slot unavailable.")
                return
            if parts[0] == "preview":
                report(player, "Preview: %d item(s)\nGenerator: %s\n%s: %s"
                       % (plan_one_slot(source, target, target_slot=target_slot),
                          self.describe_port(source), target_label, self.describe_port(target, target_slot)))
                return
            if storage.get_stack(1) is not None:
                report(player, "[IML move] Recovery slot occupied")
                return
            planned, moved = self.move_with_recovery(source, target, storage, storage,
                                                    target_slot=target_slot)
            if report == self.report_panel:
                report(player, "Planned: %d / Moved: %d\nGenerator: %s\n%s: %s\nRecovery: %s"
                       % (planned, moved, self.describe_port(source), target_label,
                          self.describe_port(target, target_slot),
                          self.describe_port(storage, 1)))
                return
            report(player, "[IML move] Planned %d / Sent %d | source: %r | target: %r | buffered: %r"
                   % (planned, moved, source.get_stack(0), target.get_stack(target_slot), storage.get_stack(1)))
            return
        if parts[0] == "seed":
            if source.get_stack(0) is not None:
                report(player, "[IML source] Seed requires an empty generator")
                return
            storage.insert(0, SAMPLE_STACK)
        before = source.get_stack(0)
        simulated = source.extract(0, 10, True)
        if report != self.report:
            target_label, target = self.transfer_target(dimension, position, "item")
            report(player, "Generator: %s\n%s: %s\nRecovery: %s\nSimulation: %s"
                   % (self.describe_port(source), target_label, self.describe_port(target),
                      self.describe_port(storage, 1),
                      "Inventory unchanged" if before == source.get_stack(0) else "Inventory changed"))
            return
        report(player, "[IML source] Stored: %r; simulated: %r; unchanged: %r"
                    % (before, simulated, before == source.get_stack(0)))

    @staticmethod
    def move_with_recovery(source, target, restore, storage, source_slot=0, target_slot=0):
        planned, moved, remainder = move_one_slot(source, target, restore, source_slot, target_slot)
        if remainder is not None and storage.insert(1, remainder) is not None:
            raise RuntimeError("Recovery slot rejected the unsent stack")
        return planned, moved

    def on_chat(self, args):
        parts = args["message"].split()
        if parts[:2] == ["imlmove", "pull"]:
            args["cancel"] = True
            player = args["playerId"]
            try:
                if len(parts) not in (5, 6):
                    raise ValueError()
                position = tuple(map(int, parts[2:5]))
                slot = int(parts[5]) if len(parts) == 6 else None
            except ValueError:
                self.report(player, "Usage: imlmove pull X Y Z [slot]")
                return
            dim = self._factory.CreateDimension(player).GetPlayerDimensionId()
            self.pull_items(player, dim, position, False, slot, self.report)
            return
        if parts[:1] == ["imlchestprobe"]:
            args["cancel"] = True
            player = args["playerId"]
            try:
                if len(parts) != 4:
                    raise ValueError()
                position = tuple(map(int, parts[1:]))
            except ValueError:
                self.report(player, "Usage: imlchestprobe X Y Z")
                return
            dimension = self._factory.CreateDimension(player).GetPlayerDimensionId()
            items = self._factory.CreateItem(serverApi.GetLevelId())
            lookup = self._fe.get_block_capability if self._fe is not None else None
            for line in describe_chest(self._blocks, items, dimension, position, lookup):
                print("[IML chest probe] " + line)
            self.report(player, "Chest probe complete. See the server log.")
            return
        if parts[:1] == ["imlpanel"]:
            args["cancel"] = True
            player = args["playerId"]
            try:
                if len(parts) != 4:
                    raise ValueError()
                position = tuple(map(int, parts[1:]))
            except ValueError:
                self.report(player, "Usage: imlpanel X Y Z")
                return
            self.open_panel(player, position)
            return
        if len(parts) >= 2 and parts[0] == "imlmove" and parts[1] in (
                "seed", "source", "send", "partial", "preview"):
            args["cancel"] = True
            self.test_stock(args["playerId"], parts[1:])
            return
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

    def open_panel(self, player, position):
        dimension = self._factory.CreateDimension(player).GetPlayerDimensionId()
        block = self._blocks.GetBlockNew(position, dimension)
        modes = {GENERATOR: "item_source", BATTERY: "battery", TANK: "tank", CONDUIT: "gather"}
        if not block or block["name"] not in modes:
            self.report(player, "Select a generator, battery, fluid tank, or Item Conduit.")
            return
        name = block["name"]
        mode = modes[name]
        if name == GENERATOR:
            x, y, z = position
            below = self._blocks.GetBlockNew((x, y - 1, z), dimension)
            if below:
                mode = {TANK: "fluid_source", CONDUIT: "batch"}.get(below["name"], mode)
        self._panel_targets[player] = (dimension, position, name, mode)
        self.NotifyToClient(player, "OpenTransferPanel", {"mode": mode})

    def on_transfer_action(self, args):
        player = args.get("__id__")
        action = args.get("action")
        if player is None:
            return
        if action == "open":
            pos = args.get("position")
            if isinstance(pos, list) and len(pos) == 3 and all(type(v) is int for v in pos):
                feet = self._factory.CreatePos(player).GetFootPos()
                if feet and sum((feet[i] - pos[i] - 0.5) ** 2 for i in range(3)) <= 64:
                    self.open_panel(player, tuple(pos))
            return
        selected = self._panel_targets.get(player)
        if selected is None or action not in ("seed", "source", "send", "partial", "preview", "pull"):
            return
        dimension, position, name, mode = selected
        if dimension != self._factory.CreateDimension(player).GetPlayerDimensionId():
            self.report_panel(player, "Reopen the panel in this dimension.")
            return
        if mode in ("fluid_source", "tank", "batch", "gather"):
            if self._fe is None:
                self.report_panel(player, "Library unavailable.")
                return
            block = self._blocks.GetBlockNew(position, dimension)
            if not block or block["name"] != name:
                self.report_panel(player, "Device unavailable.")
                return
            if mode == "gather":
                if action in ("source", "preview", "send"):
                    self.report_panel(player, run_gather_demo(
                        self._fe, self._blocks, dimension, position, action))
            elif mode == "batch":
                if action in ("seed", "source", "preview", "send"):
                    storage = self.storage_port(dimension, position)
                    self.report_panel(player, run_batch_demo(
                        self._fe, self._blocks, dimension, position, storage, SAMPLE_STACK, action))
            elif action != "pull":
                self.report_panel(player, run_fluid_demo(
                    self._fe, dimension, position, mode == "tank", action))
            return
        if mode == "battery":
            if action == "source":
                target = self.battery_port_at(dimension, position)
                storage = self.storage_port(dimension, position) if target is not None else None
                message = "Battery: " + self.describe_port(target)
                if storage is not None and storage.get_stack(1) is not None:
                    message += "\nRecovery: " + self.describe_port(storage, 1)
                self.report_panel(player, message)
            elif action in ("preview", "pull"):
                self.pull_items(player, dimension, position, action == "preview")
            return
        if action != "pull":
            self.test_stock(player, (action,) + position, self.report_panel)

    def pull_items(self, player, dimension, position, simulate, slot=None, report=None):
        report = self.report_panel if report is None else report
        target = self.battery_port_at(dimension, position)
        if target is None:
            report(player, "Battery input unavailable.")
            return
        x, y, z = position
        source = self._fe.get_block_capability(dimension, (x, y + 1, z), "down", "item")
        if source is None:
            report(player, "Connect an item output above the battery.")
            return
        slots = source.get_slots()
        if slot is None and slots:
            slot = slots[0]
        if slot not in slots:
            report(player, "Source slot unavailable.")
            return
        if simulate:
            summary = "Preview: %d item(s)" % plan_one_slot(source, target, source_slot=slot)
        else:
            storage = self.storage_port(dimension, position)
            if storage is None or storage.get_stack(1) is not None:
                report(player, "Battery recovery slot unavailable or occupied.")
                return
            planned, moved = self.move_with_recovery(source, target, source, storage, source_slot=slot)
            summary = "Planned: %d / Moved: %d" % (planned, moved)
            summary += "\nRecovery: " + self.describe_port(storage, 1)
        report(player, "%s\nSource: %s\nBattery: %s"
               % (summary, self.describe_port(source, slot), self.describe_port(target)))

    def battery_port_at(self, dimension, position):
        block = self._blocks.GetBlockNew(position, dimension)
        if self._fe is not None and block and block["name"] == BATTERY:
            return self._fe.get_block_capability(dimension, position, "up", "item")
        return None

    @staticmethod
    def describe_port(port, slot=None):
        if port is None:
            return "Unavailable"
        if slot is None:
            slots = port.get_slots()
            if not slots:
                return "Unavailable"
            slot = slots[0]
        stack = port.get_stack(slot)
        if not stack:
            return "Empty"
        item = stack.get("newItemName", "Item")
        if item == "minecraft:apple":
            item = "Apple"
        marked = (stack.get("extraId") == SAMPLE_ID
                  or (stack.get("userData") or {}).get("imlMove") == "source")
        return "%s x%d%s" % (item, stack["count"], " [marked]" if marked else "")

    def report_panel(self, player, message):
        self.NotifyToClient(player, "TransferResult", {"text": message})

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
        self.UnListenForEvent("iml_fe_source", "client", "TransferAction",
                              self, self.on_transfer_action)
        self.UnListenForEvent(self._engine_namespace, self._engine_system,
                              "LoadServerAddonScriptsAfter", self, self.register_ports)
        self.UnListenForEvent(self._engine_namespace, self._engine_system,
                              "ServerChatEvent", self, self.on_chat)
        self.UnListenForEvent(self._engine_namespace, self._engine_system,
                              "ServerBlockUseEvent", self, self.on_use)
