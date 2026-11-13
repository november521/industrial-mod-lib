# 工业模组通用前置库

本库面向《我的世界》网易基岩版 ModSDK。不同玩法组件可以通过同一个服务端系统注册和查询机器的能量和物品端口。

跨组件供电及存档恢复的测试步骤见 [FE 开发示例](examples/README.md)。

## 加载

将 `behavior_packs/industrial_mod_lib` 作为行为包加入网易开发工作台的测试工程。使用 FE 的组件需要与 FE 一起加载。若消费者使用行为包清单声明依赖，可引用 FE 清单的头部 UUID `b127e51b-699b-45bd-b82b-8b1169c87502` 和版本 `[0, 1, 0]`。

## 注册一块电池

以下代码放在消费者组件的服务端脚本里。在 FE 的服务端系统注册完成后执行一次。示例方块 `example:battery` 需要在自己的行为包中定义，并配置 `netease:block_entity`。

```python
import mod.server.extraServerApi as serverApi

fe = serverApi.GetSystem("fe", "energy")


def battery_port(dimension, position, face):
    if face == "up":
        return fe.create_block_storage(dimension, position, 10000, 200, 0)
    if face == "down":
        return fe.create_block_storage(dimension, position, 10000, 0, 200)
    return None


fe.register_block("example:battery", battery_port)
```

另一组件可以调用 `fe.get_block_energy(dimension, position, "up")` 来查找电池顶部端口。没有可用端口时返回 `None`。方块面使用 `down`、`up`、`north`、`south`、`west`、`east`，相对于被查询的方块。端口按需查询，调用方应在同一段服务端逻辑内用完，避免在区块卸载或方块替换后继续持有。

## 端口接口

- `receive_energy(amount, simulate=False)` 和 `extract_energy(amount, simulate=False)` 返回实际可充入或取出的整数 FE。传入 `simulate=True` 时只计算结果。
- `get_energy_stored()`、`get_max_energy_stored()`、`can_receive()`、`can_extract()` 用于查询端口。最后两个方法表示端口是否允许对应操作，具体能传多少由储量和容量决定。
- `create_block_storage(...)` 将能量写入方块实体。同一方块上使用相同数据键的不同面共享储量。方块实体不可用时返回 `None`。`create_storage(...)` 也可以使用调用方提供的字典式存储，省略数据参数时使用内存。

输入和输出上限按每次调用计算。末影接口的导管负责按游戏刻分配传输额度和调度网络。模拟操作不会预留电量。

## 自定义设备物品端口（开发中）

同一个 `fe` 系统提供 `register_block_capability(block_id, "item", provider)` 和
`get_block_capability(dimension, position, face, "item")`。提供器接收维度、坐标和方块面，
可调用 `create_block_item_port` 创建方块实体库存的视图：

```python
def item_port(dimension, position, face):
    if face not in ("up", "down"):
        return None
    return fe.create_block_item_port(
        dimension, position, "example:inventory", {0: 16},
        item_stack_limit, (0,) if face == "up" else (),
        (0,) if face == "down" else ())


fe.register_block_capability("example:battery", "item", item_port)
```

`item_stack_limit(stack)` 由设备提供，应返回该物品的堆叠上限。示例的顶面可插入，
底面可抽取。两面使用同一存储键和槽号，共享槽位及 `get_slot_key(slot)` 返回值。
物品堆是含整数 `count` 的字典，其他字段完整保留。当前按除 `count` 外的全部字段
比较是否可合堆，持久化数据应使用方块实体支持的值类型。

- `get_slots()` 返回该面可见的槽号，`get_slot_limit(slot)` 返回配置的槽位上限。
- `get_stack(slot)` 返回物品堆副本，空槽返回 `None`。
- `insert(slot, stack, simulate=False)` 返回余量，全部接收时返回 `None`。
- `extract(slot, count, simulate=False)` 返回取出的物品堆，无法取出时返回 `None`。

每轮操作前重新查询端口。当前实现会检查方块状态和方块实体是否可访问，
同坐标换成同类型、同状态方块时无法通过状态对比识别，因此端口仅在当前调用中使用。
用户已在 MC Studio 完成目录重构后的物品端口复验。对应的验收包位于 [mcstudio-test/current](mcstudio-test/current)。

本地验收命令（在本项目目录运行）：

```text
python -B -m unittest discover -s tests -v
```
