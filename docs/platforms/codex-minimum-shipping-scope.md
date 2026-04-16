# Codex Minimum Shipping Scope

## 文档定位

本文档只回答一个问题：**如果当前目标只是让别人从远端 clone 仓库并在 Codex 中使用，那么最小需要提交哪些内容。**

它不等于完整发布清单，也不等于整个仓库的最终收口范围。

## 核心结论

如果目标仅限于 “Codex 可导入并可发现主线技能”，最小提交面应覆盖以下内容：

### 1. 根级技能目录

必须提交：

- `skills/`

原因：

- 这是当前唯一主线技能根。
- Codex 实际发现和使用的就是这里，而不是 `superpowers/skills/`。

### 2. Codex 安装入口

必须提交：

- `.codex/INSTALL.md`

原因：

- 这是别人 clone 后能否按文档正确接入 Codex 的直接入口。

### 3. 使用说明与平台边界文档

建议一并提交：

- `README.md`
- `docs/platforms/codex-usage.md`

原因：

- `README.md` 提供仓库级入口说明。
- `codex-usage.md` 明确当前是 skill-based 软编排，不是显式 orchestrator，能减少错误预期。

### 4. 启动注入与公共入口资产

建议一并提交：

- `hooks/`
- `GEMINI.md`
- `.claude-plugin/`
- `.cursor-plugin/`
- `.opencode/`
- `package.json`
- `gemini-extension.json`

原因：

- 对“只让 Codex 用起来”来说，这些不全是硬必需。
- 但它们已经构成当前根级产品骨架，单独漏掉会让仓库看起来像半迁移态。

## 当前不属于 Codex 最小提交面的内容

以下内容当前不是“为了 Codex 可导入”必须提交的：

- `tests/`
- `docs/testing/`
- `docs/architecture/`
- `20-architecture/*`
- `10-requirements/` / `15-tech-selection/` / `25-contract/`
- legacy 相关资产
- `superpowers/` 目录整体

注意：

- 这些内容对完整项目当然重要。
- 但如果当前目标只是尽快形成一个 Codex 可导入的远端仓库，它们不是最低必要项。

## 当前不建议一起带入的噪音

当前如果只为 Codex 导入收口，不建议顺手把以下内容混进同一次最小提交：

- `.worktrees/`
- 迁移期不稳定的 legacy 清理动作
- 与 `skill/agent-in-tool/` 相关的大量删除动作
- `superpowers/.git` 退场动作

原因：

- 这些内容会把“Codex 可导入最小闭环”和“仓库整体收口”混成一次大提交，审核难度会明显上升。

## 最小提交建议

如果按最小可用原则组织提交，建议至少包含：

1. `skills/`
2. `.codex/INSTALL.md`
3. `README.md`
4. `docs/platforms/codex-usage.md`

如果按“最小可用 + 根级产品骨架一致性”组织提交，建议包含：

1. `skills/`
2. `.codex/`
3. `README.md`
4. `docs/platforms/`
5. `hooks/`
6. `GEMINI.md`
7. `.claude-plugin/`
8. `.cursor-plugin/`
9. `.opencode/`
10. `package.json`
11. `gemini-extension.json`

## 结论

当前如果只是为了让仓库“先能被 Codex 导入并使用”，完全没必要等整个重组结束。

但前提是：**必须把根级 `skills/` 和 Codex 接入文档真正提交到远端。**
