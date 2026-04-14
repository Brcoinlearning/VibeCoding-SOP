# Agent-in-Tool Skill（规范版）

当前仓库只保留可落地、可闭环的 4 个本地 Skill：

1. `forge_requirements`：需求落盘（`10-requirements/` + `20-planning/`）
2. `enforce_tdd`：TDD 三门禁证据（`30-build/`）
3. `trigger_blind_review`：独立盲审并产出报告（`40-review/`）
4. `submit_to_owner`：Owner 最终 Go/No-Go 与发布归档（`50-release/`）

并新增 2 个总控 Skill（阶段拆分 + 可联通）：

5. `requirements_phase_orchestrator`：控制需求分析阶段状态与门禁
6. `development_phase_orchestrator`：控制开发发布阶段状态与门禁

## 保留与抛弃

| 项目 | 结论 | 说明 |
|---|---|---|
| `forge_requirements` | 保留 | 本地执行链起点 |
| `enforce_tdd` | 保留 | 工程化门禁核心 |
| `trigger_blind_review` | 保留 | 独立审查与结构化报告 |
| `submit_to_owner` | 保留 | 唯一放行入口 |
| `requirements_phase_orchestrator` | 保留 | 需求阶段总控 |
| `development_phase_orchestrator` | 保留 | 开发阶段总控 |
| `read_task_contract` | 抛弃 | 已被原生文件读取能力替代 |
| “手工跨窗口搬运日志/diff” | 抛弃 | 改为脚本采集和路由 |

## 与外部 Skill 的衔接

```text
阶段一（收敛边界）:
reverse-interviewing -> interview-conducting -> elicitation-methodology
阶段二（架构拆解）:
architecture-patterns -> decomposition-planning-roadmap
阶段三（契约固化）:
tdd
进入本仓库:
forge_requirements -> enforce_tdd -> trigger_blind_review -> submit_to_owner
```

## 两个总控的联通方式

1. 需求总控执行完成后，生成 `20-planning/{task_id}-requirements_handoff.json`
2. 开发总控 `dev-init` 默认要求存在该交接文件
3. 交接文件满足时，开发四步链才进入强门禁流程

## 个人开发执行顺序（唯一推荐）

```bash
python3 cli.py forge-contract TASK-001 "原始需求" --workspace .
python3 cli.py tdd-enforce TASK-001 --workspace . --test-command "pytest -q"
python3 cli.py blind-review TASK-001 --workspace .
python3 cli.py submit-owner TASK-001 --workspace .
```

## 最小门禁要求

1. 未生成 `20-planning/{task_id}.md`：不得进入编码。
2. `tdd-enforce` 非 PASS：不得进入盲审。
3. 盲审结果非 PASS：不得进入 Owner 裁决。
4. Owner 未 Go：不得进入 `50-release/`。
