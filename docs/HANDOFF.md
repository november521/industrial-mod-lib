# Industrial Mod Lib 项目交接

中文名为「工业模组通用前置库」，目标是网易《我的世界》中国版基岩版 ModSDK。项目位于工作区的 `Industrial Mod Lib/`。

本阶段已完成方块 FE、物品和流体端口，以及原版容器适配和两套独立示例。当前验收版本为前置库 **0.1.5**，公开接口为 **API v1**。按[接入指南](API.md)使用，待补的实机项目集中在[验收记录](TESTING.md)。

## Git

- IML 项目目录是本地 Git 仓库根目录。已将 `origin` 配置为 [november521/industrial-mod-lib](https://github.com/november521/industrial-mod-lib) 的 HTTPS 地址。
- GitHub CLI 已核验登录账号为 `november521`，远程仓库为公开仓库。本地提交身份沿用当前配置的 `novembersyy1`。
- 历史验收 ZIP 保存在本地 `mcstudio-test/archive/`，当前验收包随项目维护。

## 已确定的首版范围

- 交付独立前置库、第三方接入文档和两个分别打包的开发示例。末影接口另立项目。
- 统一按维度、坐标、方块面和能力类型查询，公开模拟及实际存取。能量覆盖方块设备，物品覆盖自定义设备、原版箱子、木桶和潜影盒，流体覆盖机器和储罐，以水、岩浆验收。
- 手动一对多和多对一留作前置库验收示例。多对多、路由、过滤、优先级和自动调度归末影接口的管道组件。
- 正式测试环境为 MC Studio 的本地基岩版开发测试。详细要求见 [项目规格](PROJECT_SPEC.md)，目录规划见 [开发文档](DEVELOPMENT.md)。

## 实现和验证状态

- `behavior_packs/industrial_mod_lib/` 已实现整数 FE、按面注册与查询、模拟和实际充放电，以及方块实体存储。现有入口为 `GetSystem("fe", "energy")`，限额按调用计算。
- `examples/source/` 和 `examples/receiver/` 分别是发电机和电池。已确认三个独立行为包同时挂载，两个示例方块成功注册。工作台打包故障及复用步骤见 [MC Studio 测试说明](MCSTUDIO.md)。
- FE 供电示例提供聊天测试入口。实际供电和最新三包的新存档回归仍待实测，步骤见[验收记录](TESTING.md#下次实机复验)。
- 统一能力注册表和自定义物品端口已实现。用户已确认发电机与电池的 0.1.3 跨包物品搬运实机验收通过。[验收步骤](../examples/README.md#跨组件物品搬运验收)
- 用户已确认单箱和双箱通过 MC Studio 实机验收。双箱探针实测两半均返回 54 格，两个标记出现在两半的同一槽号 0 和 27。[双箱搬运验收步骤](../examples/README.md#原版双箱搬运验收)
- 用户已确认流体储罐通过 MC Studio 实机验收。发电机和储罐可演示水、岩浆、拒绝混装和存档恢复。[流体验收步骤](../examples/README.md#流体验收)
- 用户已确认手动一对多通过 MC Studio 实机验收。发电机通过下方导管向下和向东分流。[一对多验收步骤](../examples/README.md#一对多物品搬运验收)
- 用户已确认普通箱的手动多对一通过 MC Studio 实机验收。两个箱子共享一块电池的容量。[多对一验收步骤](../examples/README.md#多对一物品搬运验收)
- IML 已内置木桶和潜影盒物品端口，导管按方块面查询通用端口。已通过本地测试，待 MC Studio 核对槽位收发、防嵌套和装有物品的潜影盒搬运。[木桶与潜影盒验收步骤](../examples/README.md#木桶与潜影盒验收)
- 用户已确认陷阱箱与铜箱本轮 MC Studio 验收通过。陷阱箱和 8 种铜箱与普通箱共享物品端口适配。[箱子变种验收步骤](../examples/README.md#陷阱箱与铜箱验收)

## 给新对话的起点

开发者从[接入指南](API.md)开始。维护者可查看[项目规格](PROJECT_SPEC.md)、[开发文档](DEVELOPMENT.md)和[验收记录](TESTING.md)。[验收目录](../mcstudio-test/acceptance)存放当前三个包，历史验收包在 `mcstudio-test/archive/`。同一个世界只挂载同 UUID 的一个版本。
