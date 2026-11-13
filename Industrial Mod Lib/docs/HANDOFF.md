# Industrial Mod Lib 项目交接

中文名为「工业模组通用前置库」，目标是网易《我的世界》中国版基岩版 ModSDK。项目位于工作区的 `Industrial Mod Lib/`。

## Git

- 工作区根目录是本地 Git 仓库。已将 `origin` 配置为 [november521/industrial-mod-lib](https://github.com/november521/industrial-mod-lib) 的 HTTPS 地址。
- GitHub CLI 已核验登录账号为 `november521`，远程仓库为公开仓库。本地提交身份沿用当前配置的 `novembersyy1`。
- 历史验收 ZIP 保存在本地 `mcstudio-test/archive/`，当前验收包随项目维护。

## 已确定的首版范围

- 交付独立前置库、第三方接入文档和两个分别打包的开发示例。末影接口另立项目。
- 统一按维度、坐标、方块面和能力类型查询，公开模拟及实际存取。能量只覆盖方块设备，物品覆盖自定义设备和原版单箱、双箱，流体覆盖机器和储罐，以水、岩浆验收。
- 批量搬运暂在示例中实现和验证。包含一对多、多对一、多对多，共享实际槽位容量，按实际执行结果结算。公开 API 先覆盖端口。
- 正式测试环境为 MC Studio 的本地基岩版开发测试。详细要求见 [项目规格](PROJECT_SPEC.md)，目录规划见 [开发文档](DEVELOPMENT.md)。

## 实现和验证状态

- `behavior_packs/industrial_mod_lib/` 已实现整数 FE、按面注册与查询、模拟和实际充放电，以及方块实体存储。现有入口为 `GetSystem("fe", "energy")`，限额按调用计算。
- `examples/source/` 和 `examples/receiver/` 分别是发电机和电池。已确认三个独立行为包同时挂载，两个示例方块成功注册。工作台打包故障及复用步骤见 [网易模组开发笔记](../../NETEASE_MODSDK_NOTES.md)。
- 旧示例空手右键没有成功。0.1.2 示例改用聊天测试入口补充交互，已检查语法和 ZIP 结构。实际供电、0.1.2 聊天入口和存档恢复仍未实测。用户已明确本阶段结束 FE 验证，后续默认从下一模块继续。
- 统一能力注册表和自定义物品端口已实现。用户已确认目录重构后的前置包通过 MC Studio 实机复验。跨包物品搬运、普通箱子和双箱适配、流体及批量示例待实现。

## 给新对话的起点

先读本文件、[项目规格](PROJECT_SPEC.md)和[网易模组开发笔记](../../NETEASE_MODSDK_NOTES.md)。重构复验使用 [当前前置测试包](../mcstudio-test/current/IML-fe-structure-test.zip) 和 [接收端测试包](../mcstudio-test/current/IML-receiver-item-test.zip)。历史测试包在 `mcstudio-test/archive/`，同一个世界只挂载同 UUID 的一个版本。
