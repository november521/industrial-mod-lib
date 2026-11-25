# Industrial Mod Lib 开发文档

IML 面向网易《我的世界》基岩版 ModSDK。公开接口、测试场景及详细状态见[接入指南](API.md)和[验收记录](TESTING.md)。

## 当前文件结构

```text
.
├── README.md
├── docs/
│   ├── API.md               # 第三方依赖、注册、查询和端口约定
│   ├── PROJECT_SPEC.md      # 首版交付边界
│   ├── TESTING.md           # 验收结果与待实测场景
│   ├── MCSTUDIO.md          # 导入、打包与日志排查
│   └── HANDOFF.md           # 阶段成果与维护交接
├── behavior_packs/industrial_mod_lib/
│   ├── manifest.json
│   └── IndustrialModLibScripts/
│       ├── modMain.py       # 注册 fe / energy 服务
│       ├── server.py        # 公共入口和 ModSDK 组件接入
│       ├── capabilities/registry.py
│       ├── energy.py
│       ├── items.py
│       ├── fluids.py
│       └── vanilla/
│           ├── chest.py    # 箱子名单及单双箱配对
│           └── container.py # 通用原版槽位读写、物品数据与限制
├── examples/
│   ├── source/             # 发电机、面板、搬运和探针脚本
│   └── receiver/           # 电池、储罐和导管方块
├── tests/                  # 可脱离引擎运行的 Python 测试
└── mcstudio-test/acceptance/ # 当前 MC Studio 验收包
```

源端和接收端各有独立行为包和资源包，通过公开 API 使用 IML。包结构和空 `entities/` 条目沿用 [MC Studio 开发笔记](MCSTUDIO.md)记录的规则。

## 模块间调用

1. `modMain.py` 注册服务端系统。第三方模组在服务端脚本加载后取到系统实例，检查 API 版本并注册自己的提供器。
2. `server.py` 根据维度、坐标、方块面和能力类型查找端口。原版容器适配由 IML 内置注册，提供器按方块状态与权限返回端口。
3. 物品、流体和能量端口处理各自的模拟与存取。调用方在每轮开始重新查询端口。物品路由使用 `get_slot_key` 识别同一物理格，实际搬运以端口返回量结算。
4. 示例源端脚本中的 `transport.py`、`item_batch.py` 和 `fluid_transport.py` 演示手动搬运和余量恢复。正式管网与调度由末影接口项目实现。

行为包脚本使用 Python 2.7 兼容语法，本地测试用 Python 3。包依赖使用清单版本，脚本兼容性使用 `api_version`。现有存档依赖前置包 UUID、`GetSystem("fe", "energy")` 和已使用的方块实体存储键，修改这些入口或键值前应考虑迁移。
