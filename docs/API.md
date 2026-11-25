# IML 服务端接入指南

当前验收包使用前置库版本 `0.1.5`，服务端接口版本为 `api_version = 1`。包版本用于行为包依赖，接口版本用于脚本判断调用约定。

## 加载与注册

在同一个网易基岩版 ModSDK 测试世界加载 IML 和自己的行为包。在自己的行为包 `manifest.json` 中把以下条目加入 `dependencies`，保留已有条目。

```json
{
  "uuid": "b127e51b-699b-45bd-b82b-8b1169c87502",
  "version": [0, 1, 5]
}
```

以下方法放进自己的服务端系统类。用自己的命名空间替换 `example`，并为示例方块 `example:machine` 配置 `netease:block_entity`。服务端系统由自己的模组入口注册。运行脚本使用 ModSDK 的 Python 2.7 兼容语法。

```python
import mod.server.extraServerApi as serverApi

ServerSystem = serverApi.GetServerSystemCls()
MACHINE = "example:machine"


class MachineSystem(ServerSystem):
    def __init__(self, namespace, system_name):
        ServerSystem.__init__(self, namespace, system_name)
        self.iml = None
        self.ListenForEvent(
            serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(),
            "LoadServerAddonScriptsAfter", self, self.register_ports)

    def register_ports(self, args):
        if self.iml is not None:
            return
        iml = serverApi.GetSystem("fe", "energy")
        if iml is None or getattr(iml, "api_version", None) != 1:
            print("[Example] IML API version 1 is required.")
            return
        self.iml = iml
        iml.register_block_capability(MACHINE, "energy", self.energy_port)
        iml.register_block_capability(MACHINE, "item", self.item_port)
        iml.register_block_capability(MACHINE, "fluid", self.fluid_port)

    def energy_port(self, dimension, position, face):
        if face == "up":
            return self.iml.create_block_storage(
                dimension, position, 1000, 200, 0, key="example:energy")
        if face == "down":
            return self.iml.create_block_storage(
                dimension, position, 1000, 0, 200, key="example:energy")
        return None

    def item_port(self, dimension, position, face):
        if face not in ("up", "down"):
            return None
        return self.iml.create_block_item_port(
            dimension, position, "example:items", {0: 16}, None,
            (0,) if face == "up" else (), (0,) if face == "down" else ())

    def fluid_port(self, dimension, position, face):
        if face not in ("up", "down"):
            return None
        return self.iml.create_block_fluid_port(
            dimension, position, "example:tank", 1000,
            allowed_fluids=("minecraft:water", "minecraft:lava"),
            can_fill=face == "up", can_drain=face == "down")
```

同一「方块 ID、能力类型」只注册一个提供器，重复注册会抛出 `ValueError`。提供器接收维度、坐标和方块面，返回端口或 `None`。同一设备的不同面用相同数据键共享一份储量，各自开放存取权限。共享槽位的配置、容量和流体允许列表应一致。

## 查询与存取

使用 `get_block_capability(dimension, position, face, capability)` 查询目标。方块面取 `down`、`up`、`north`、`south`、`west` 或 `east`，相对于**被查询的方块**。目标方块、能力或端口不可用时返回 `None`。旧的 `register_block(block_id, provider)` 和 `get_block_energy(dimension, position, face)` 仍可用于能量能力。

以下片段假定调用方已取得 `iml`、`dimension` 和 `position`，并且拥有要写入的测试资源。先预览，再对实际返回量结算。

```python
energy = iml.get_block_capability(dimension, position, "up", "energy")
if energy is not None:
    expected_fe = energy.receive_energy(200, simulate=True)
    accepted_fe = energy.receive_energy(expected_fe)

items = iml.get_block_capability(dimension, position, "up", "item")
if items is not None and items.get_slots():
    slot = items.get_slots()[0]
    stack = {"newItemName": "minecraft:apple", "count": 5}
    expected_remainder = items.insert(slot, stack, simulate=True)
    remainder = items.insert(slot, stack)
    accepted_items = stack["count"] - (remainder["count"] if remainder else 0)

tank = iml.get_block_capability(dimension, position, "up", "fluid")
if tank is not None:
    expected_water = tank.fill("minecraft:water", 500, simulate=True)
    accepted_water = tank.fill("minecraft:water", expected_water)
```

| 能力 | 查询 | 存取和返回值 |
| --- | --- | --- |
| 能量 | `get_energy_stored()`、`get_max_energy_stored()`、`can_receive()`、`can_extract()` | `receive_energy(amount, simulate=False)`、`extract_energy(amount, simulate=False)` 返回实际量，单位是整数 FE。端口限额按调用计算。 |
| 物品 | `get_slots()` 返回槽号，`get_stack(slot)` 返回物品堆副本或 `None`，`get_slot_limit(slot)` 返回该槽配置的上限 | `insert(slot, stack, simulate=False)` 返回余量，全部接收时返回 `None`。`extract(slot, count, simulate=False)` 返回抽出的物品堆，无物品可取时返回 `None`。 |
| 流体 | `get_fluid()` 返回 `(fluid_id, amount)` 或 `None`，`get_capacity()` 返回配置容量 | `fill(fluid_id, amount, simulate=False)`、`drain(fluid_id, amount, simulate=False)` 返回实际量，单位是整数 mB，约定 1000 mB 为一桶。 |

物品堆使用 ModSDK 字典，带整数 `count`。保留名称、附加值和自定义数据。自定义设备可传入 `item_limit(stack)` 决定堆叠上限，或传 `None` 使用 IML 的物品上限查询。设备另可用 `create_storage(capacity, max_receive, max_extract, data=None, key="fe:energy")` 创建基于字典的能量端口。

## 生命周期与结算

- 每轮开始按需查询端口，在同一段服务端操作内用完。方块替换、双箱合并或拆分、区块卸载或重载后重新查询。仅凭相同的坐标和方块状态无法识别所有替换情况。
- 模拟只返回当前可执行量或余量，库存保持原样，也不会预留容量。实际搬运以实际返回值为准。设备之间搬运时，调用方负责把未送达的物品退回来源或放入自己可追踪的缓冲。
- 按 `get_slot_key(slot)` 判断端口是否指向同一物理槽位。原版双箱的两半访问同一格时返回相同标识。按实际库存和槽位扣减额度，避免重复读取或分配同一份库存。
- IML 的公开接口提供方块能力。管道组件负责路由、多对多分配、用户过滤、优先级、轮询和重试。

[完整示例与实机步骤](../examples/README.md) · [验收状态](TESTING.md)
