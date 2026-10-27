# Personal Work Agent

面向个人工作的技能包，当前版本 **0.9.8**。

## 包含的技能

- **personal-work-agent**：根据任务选择工作流，覆盖现有代码维护、办公文档与投资研究，并执行相应的权限检查和结果验证。
- **project-builder**：从已确认的需求开始构建新软件项目，推进到可运行、可验证的首版。

## 文件结构

- `skills/`：两个技能的入口、参考说明、脚本和模板。
- `.codex-plugin/plugin.json`：Codex 插件元数据。
- `assets/`：插件图标。
- `templates/`：保留兼容性的输出模板。
- `evals/`：结构校验、单元测试、评估规则和测试素材。
- [USAGE.md](USAGE.md)：完整使用说明、宿主兼容性与校验方式。
- [CHANGELOG.md](CHANGELOG.md)：版本记录。

## 使用示例

在支持相应技能并已完成安装的环境中，按实际技能目录中的名称调用：

```text
用 $personal-work-agent 检查这个项目的问题，完成修复并验证结果。
用 $project-builder 根据下面的需求构建一个可本地运行的首版。
```

个人偏好位于 `skills/personal-work-agent/references/user-profile.md`，仅作为任务和项目未指定时的默认值。请勿写入密码、令牌、私钥或其他认证信息。

本仓库保留技能源码、使用文档与校验材料；结构校验通过不代表所有模型行为场景均已通过。不同宿主的安装方式见 [USAGE.md](USAGE.md) 和技能的宿主兼容性说明。
