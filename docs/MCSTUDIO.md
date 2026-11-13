# 网易基岩版 ModSDK 开发笔记

- **打包**：以 MC Studio 原生导出的 ZIP 为模板。已实测可用的结构是根目录直接放 `behavior_pack_*/` 和 `resource_pack_*/`，各自带 `manifest.json`。行为包的空 `entities/` 必须作为 ZIP 目录条目保留。本机 3.10 开发测试中，仅删除该条目就会导致行为包漏挂载。
- **查加载**：方块 ID 找不到时，先查本次 `*.cppconfig` 的 `world_info.behavior_packs`，再到 `%APPDATA%/MinecraftPE_Netease/logs/` 查 `Pack Stack` 和 `registerBlock name:`。工作台勾选组件后仍可能漏挂行为包。
- **查交互**：方块能放置后，再单独验证事件是否触发。`ServerBlockUseEvent` 文档面向新版自定义方块，旧版定义的空手右键需要实测。 [ModSDK 事件索引](https://github.com/MCNeteaseDevs/mc-netease-sdk/blob/main/1-ModAPI/事件/事件索引表.md)
