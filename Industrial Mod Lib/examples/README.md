# FE 跨组件开发示例

在网易开发工作台的同一个本地基岩版测试工程中加入以下包。保持各包的清单和脚本目录层级。

| 组件 | 行为包 | 资源包 |
| --- | --- | --- |
| 工业模组通用前置库 | [FE](../behavior_packs/industrial_mod_lib) | 无 |
| 脉冲发电机 | [fe_source](source/behavior_packs/fe_source) | [fe_source](source/resource_packs/fe_source) |
| 测试电池 | [fe_receiver](receiver/behavior_packs/fe_receiver) | [fe_receiver](receiver/resource_packs/fe_receiver) |

两个示例各自依赖前置包。发电机只通过 FE 查询下方方块的顶面端口，电池组件独立注册端口。创造模式可使用以下指令获得方块。

```mcfunction
/give @s iml_fe_source:generator
/give @s iml_fe_receiver:battery
```

1. 放置电池（铁块外观），将发电机（金块外观）紧贴放在电池正上方。查看工作台的服务端脚本日志，确认出现 `[FE receiver] Battery ports registered`。
2. 空手短按使用发电机。每次收到的使用事件最多发送 200 FE，日志显示实际送达和电池储量。持续按住可能产生多次事件。空手使用电池可查看当前储量。
3. 在充满前记下当前储量。保存退出并重新进入存档，直接使用电池核对电量。发电机由使用事件触发，重进期间电池电量应保持记录值。
4. 继续充至 1000 FE。再次使用发电机应记录送达 0 FE。将发电机移到电池侧面或下方后再使用，日志应提示发电机下方没有可接入的端口。
5. 在同一世界走远使区块卸载，再返回读取电池。确认储量与离开前一致，并尝试使用发电机验证端口可重新查询。

当前示例验证范围是 FE。工作台实机结果、游戏版本和工作台版本应随验收记录。
