# Agent-in-Tool Skill 概要（执行版）

## 当前保留项

1. `forge_requirements`
2. `enforce_tdd`
3. `trigger_blind_review`
4. `submit_to_owner`

## 当前淘汰项

1. `read_task_contract`（已移除）
2. 手工搬运日志与 diff（改为脚本采集）
3. 未经门禁直接放行（禁止）

## 标准衔接链路

外部需求技能（阶段一/二/三）产出需求上下文后，进入本地四步链路：

`forge_requirements` -> `enforce_tdd` -> `trigger_blind_review` -> `submit_to_owner`

## 工程化门禁

1. 需求门禁：必须存在 `20-planning/{task_id}.md`。
2. 测试门禁：`tdd-enforce` 三门（RED/GREEN/REFACTOR）必须满足策略。
3. 审查门禁：盲审结论必须结构化且状态为 PASS。
4. 发布门禁：仅 Owner Go 可进入发布归档。
