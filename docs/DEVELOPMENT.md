# Industrial Mod Lib 开发文档

工业模组通用前置库面向网易《我的世界》基岩版 ModSDK。它让不同的行为包以相同方式查询方块的能量、物品和流体端口。设计范围与验收条件见 [项目规格](PROJECT_SPEC.md)，现有能量原型的接入方式见 [README](../README.md)。

## 当前文件结构

```text
Industrial Mod Lib/
├── README.md
├── docs/                              # 规格、开发说明和交接记录
├── behavior_packs/industrial_mod_lib/
│   ├── manifest.json
│   └── IndustrialModLibScripts/
│       ├── __init__.py
│       ├── modMain.py                 # 注册 fe / energy
│       ├── server.py                  # 能力查询和方块实体接入
│       ├── capabilities/
│       │   ├── __init__.py
│       │   └── registry.py            # 注册和查找能力提供器
│       ├── energy.py
│       └── items.py
├── examples/                          # 源端和接收端独立组件
├── tests/                             # 本地逻辑测试
└── mcstudio-test/
    ├── current/                       # 当前实机验收包
    └── archive/                       # 历史验收与故障对照包
```

工作台加载的行为包根目录是 `behavior_packs/industrial_mod_lib`，其中 `manifest.json` 与脚本目录同级。服务端初始化时，`modMain.py` 注册 `EnergySystem`。调用方通过 `GetSystem("fe", "energy")` 取得系统。查询能量端口时，`server.py` 按坐标读取方块标识，选择对应提供器并传入目标方块面。提供器可用 `create_block_storage` 将储量写入方块实体的 `fe:energy` 字段。当前输入输出上限按调用计算。

目前另有 [FE 开发示例](../examples/README.md)。`examples/source/` 和 `examples/receiver/` 各有独立行为包及配套资源包，分别实现手动脉冲供电和持久化电池。

## 首版目标结构

下图是首版建议布局。目标目录中的模块、完整示例和测试文件是计划项，名称可在实现中随职责调整。

```text
.
├── README.md                              # 项目介绍、安装入口和文档链接
├── docs/
│   ├── PROJECT_SPEC.md
│   ├── DEVELOPMENT.md
│   ├── HANDOFF.md
│   ├── API.md                             # 公开接口、返回值、版本及生命周期
│   └── TESTING.md                         # 工作台装载步骤、测试场景和实测记录
├── behavior_packs/
│   └── industrial_mod_lib/
│       ├── manifest.json                  # 前置行为包标识、显示名和版本
│       └── IndustrialModLibScripts/
│           ├── __init__.py                # Python 脚本包标记
│           ├── modMain.py                 # 注册前置的 ModSDK 服务端系统
│           ├── server.py                  # 公开服务入口、ModSDK 组件初始化
│           ├── capabilities/registry.py                # 按方块 ID 和能力类型注册提供器
│           ├── energy.py                  # 迁入 FE 储能、模拟和实际收发逻辑
│           ├── items.py                   # 物品端口、堆叠规则和自管库存
│           ├── fluids.py                  # 流体端口、流体标识和单流体储罐
│           └── vanilla_chest.py           # 原版单箱、双箱的 ModSDK 槽位适配
├── examples/
│   ├── source/
│   │   ├── behavior_packs/source_demo/
│   │   │   ├── manifest.json              # 源端组件标识与前置依赖
│   │   │   ├── blocks/                    # 能量、物品和流体源端方块定义
│   │   │   └── IndustrialModLibSourceDemoScripts/
│   │   │       ├── __init__.py            # Python 脚本包标记
│   │   │       ├── modMain.py             # 注册示例服务端系统
│   │   │       └── server.py              # 初始化源端并注册三类能力
│   │   └── resource_packs/source_demo/    # 源端资源清单及展示所需资源
│   └── transport/
│       ├── behavior_packs/transport_demo/
│       │   ├── manifest.json              # 接收端组件标识与前置依赖
│       │   ├── blocks/                    # 接收设备和简单导管的方块定义
│       │   └── IndustrialModLibTransportDemoScripts/
│       │       ├── __init__.py            # Python 脚本包标记
│       │       ├── modMain.py             # 注册示例服务端系统
│       │       ├── server.py              # 注册接收设备、驱动导管更新
│       │       └── transport.py           # 分配容量、执行搬运和处理未送达余量
│       └── resource_packs/transport_demo/ # 接收端资源清单及展示所需资源
└── tests/
    ├── test_energy.py                     # 储能边界、按次限额和模拟无副作用
    ├── test_items.py                      # 合堆、余量、物品数据和槽位权限
    ├── test_fluids.py                     # 类型匹配、满罐与空罐
    ├── test_registry.py                   # 注册冲突、按面查询和空端口
    └── test_vanilla_chest.py               # 模拟 SDK 的单箱、双箱映射与写入失败
```

各资源包包含自己的 `manifest.json` 和示例方块显示所需的资源。工作台分别加载前置行为包与两个示例组件各自的行为包、资源包。两个示例分别依赖前置，通过公开系统查询端口，可以独立装载。仓库内的文档和测试目录用于开发。

## 模块间调用

1. `modMain.py` 注册服务端系统。第三方组件在服务可用后取得系统实例，检查 API 版本，再注册自定义方块的提供器。
2. `server.py` 接收维度、坐标、目标方块面和能力类型，调用 ModSDK 识别方块，然后从 `capabilities/registry.py` 选择提供器。原版箱子由库初始化时注册物品提供器。
3. 提供器返回指定面的端口。能量、物品和流体模块处理各自的模拟与实际存取规则。原版箱子的底层读写集中在 `vanilla_chest.py`，公开接口遵守与自定义库存相同的语义。
4. 导管通过公开端口读取或变更资源。示例的 `transport.py` 处理多来源和多目标的分配，依据实际操作结果结算。导管的路由、优先级和重试都在示例组件内。

### 实现约定

- **接口与库存身份。** 方块面控制访问权限。物品端口还需提供用于判断底层库存及槽位是否相同的信息。双箱从两半访问时，必须映射到同一份库存及一致的槽位身份。映射和大箱合并、拆分行为以工作台实测为准。
- **模拟与实际执行。** 模拟读取当前状态并计算结果。实际插入以实际接受量结算，物品插入返回余量，抽取返回实际取得的物品堆。传递物品时保留自定义数据。
- **区块与存档。** 端口按需获取。拆除、替换、改朝向或卸载区块后重新查询。方块自管状态使用方块实体数据持久化。示例处理目标拒收和部分接收时，保留对未送达物品的归属。
- **运行时。** 行为包脚本沿用 FE 原型的 Python 2.7 兼容语法。ModSDK 调用集中在入口、服务端接入和原版容器适配代码，便于本地验证储存和注册逻辑。
- **迁移。** 改用正式显示名和脚本目录时，同步更新系统注册路径。计划保留原型行为包头部 UUID 与 `fe:energy` 数据键。原型的 `GetSystem("fe", "energy")` 与统一服务的兼容策略随首版 API 文档确定。

## 开发与验证顺序

1. **统一注册与能量。** 将现有能量逻辑接入通用注册表，验证两个独立示例能在同一工作台存档里注册与查询，记录工作台和游戏版本。
2. **物品与箱子。** 先让自定义库存和单箱走同一接口，再验证双箱两半、合并与拆分，以及部分写入、物品数据保留和端口失效。
3. **流体。** 加入设备间注入、抽取和单流体储罐，用水和岩浆验证类型匹配、容量及存档恢复。
4. **批量搬运。** 用示例复现一对多、多对一、多对多。检查源端、目标端和缓冲的物品总量，并记录正常、部分接收和满箱场景的读写次数及每轮耗时。
5. **接入验收。** 按公开文档从空测试世界装载三个组件，复验跨组件互通、存档重进和区块重新加载。测试脚本覆盖可脱离引擎的规则，实际 ModSDK 行为以工作台记录为准。
