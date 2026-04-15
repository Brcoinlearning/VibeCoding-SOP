---
name: development-transparency-protocol
description: 用于正式开发阶段的透明度协议，统一约束 task 开始说明、implementer 调用说明、reviewer 调用说明、task 完成汇报，以及高风险改动预览后写入门禁
---

# Development Transparency Protocol

## 技能定位

这是正式开发阶段的公共协议 skill。

它不负责需求分析、技术选型、架构设计或测试契约本身，也不直接负责具体实现。它只做一件事：把正式开发阶段所有面向 Owner 的关键说明动作标准化，让主控 agent 和子 agent 都不能闷头推进。

## 适用范围

本协议适用于以下场景：

- 进入某个新 task 前
- 准备调用 implementer subagent 前
- implementer 准备进行高风险写入前
- implementer 完成后准备进入 review 前
- reviewer 调用前
- 当前 task 完成、准备进入下一 task 前

## 核心原则

### 原则 1：先说明，再行动

凡是会改变流程状态、写入文件、调用子 agent、进入 review 的动作，都必须先向 Owner 说明，再继续执行。

### 原则 2：说明必须可核对

说明不能停留在“我要开始做了”这种空话，必须让 Owner 能核对：

- 读了什么
- 要做什么
- 预计改哪里
- 接下来调用谁

### 原则 3：高风险任务必须预览后写入

如果改动范围大、影响关键边界、或存在较高回滚成本，就不能直接写文件，必须先给 Owner 看预览。

### 原则 4：review 必须显式可见

Owner 必须能看到 reviewer 即将被调用、调用目的是什么、review 结果是什么。

## 输出要求

本协议不产出独立阶段文档。

它产出的是正式开发过程中的标准化说明文本。必要时，这些说明可以同步沉淀到进度文档，但本协议本身不要求固定写入单独文件。

## 模板 1：task 启动说明

适用时机：

- 某个新 task 准备开始
- implementer 尚未被调用

必须包含：

- 当前 task 名称
- 实际读取的前置文档
- 本轮目标
- 预计触达的文件或文件类型
- 下一步将调用的 implementer

推荐模板：

```text
当前 task：<task 名称>

我已读取：
- <路径 1>
- <路径 2>

本轮目标：<本轮要完成什么>
预计触达：<文件路径或文件类型>
下一步：调用 implementer subagent 执行当前 task

请确认我按这个范围开始。
```

## 模板 2：implementer 调用说明

适用时机：

- 主控 agent 准备正式调用 implementer subagent

必须包含：

- implementer 的职责
- 本次只允许做什么
- 本次不允许做什么

推荐模板：

```text
即将调用 implementer subagent。

本次职责：<实现目标>
允许动作：<实现、测试、局部重构等>
禁止动作：<越界改动、跳过 review、自行放行等>

若 implementer 在执行中发现上下文不足、任务过大或依赖不明，应立即返回，不得自行猜测推进。
```

## 模板 3：高风险预览后写入说明

适用时机：

- task 被判定为高风险
- implementer 准备写入关键文件

高风险判断信号至少包括：

- 影响多个关键边界
- 改动多个核心文件
- 会改变正式开发主链行为
- 回滚成本高

必须包含：

- 为什么它是高风险
- 本次预览涉及哪些文件
- 预览后若获确认才允许写入

推荐模板：

```text
当前任务属于高风险改动，暂不直接写入。

高风险原因：<原因>
预计改动文件：
- <路径 1>
- <路径 2>

预览摘要：
- <改动点 1>
- <改动点 2>

请确认是否按此预览继续正式写入。
```

## 模板 4：spec reviewer 调用说明

适用时机：

- implementer 完成当前 task
- 准备进入 spec review

必须包含：

- 当前 task 名称
- 即将调用 spec reviewer
- spec reviewer 的目标

推荐模板：

```text
当前 task 的实现已完成，准备进入第一道审查。

即将调用：spec reviewer subagent
审查目标：核对实现是否严格符合 task 目标，是否有遗漏、误解或额外实现。

该 reviewer 必须是独立 fresh subagent，不允许由 implementer 自审自放行。
```

## 模板 5：code quality reviewer 调用说明

适用时机：

- spec review 已通过
- 准备进入 code quality review

必须包含：

- 当前 task 名称
- 即将调用 code quality reviewer
- code quality reviewer 的目标

推荐模板：

```text
当前 task 已通过 spec review，准备进入第二道审查。

即将调用：code quality reviewer subagent
审查目标：检查代码质量、测试有效性、可维护性，以及是否存在放过风险问题的情况。

该 reviewer 必须是独立 fresh subagent，不允许与 implementer 复用身份。
```

## 模板 6：task 完成汇报

适用时机：

- 当前 task 已完成实现与 review
- 准备进入下一 task 前

必须包含：

- 改了什么
- 跑了什么测试
- 哪两道 review 是否通过
- 是否有残留问题

推荐模板：

```text
当前 task 已完成。

改动摘要：
- <改动点 1>
- <改动点 2>

测试结果：<执行了哪些测试，结果如何>
审查结果：
- spec review：<PASS / FAIL>
- code quality review：<PASS / FAIL>

残留问题：<列表；若没有则明确写“无”>

确认无误后，再进入下一 task。
```

## 最小透明度检查清单

每个 task 至少必须完成以下 4 个动作：

1. 开始前说明
2. reviewer 调用说明
3. 完成后汇报
4. 高风险任务执行预览后写入

如果任一动作缺失，则当前 task 不应视为流程合格。

## 与其他 skill 的关系

- `subagent-driven-development` 负责正式开发的执行骨架。
- 本协议负责给这条执行骨架提供统一的面向 Owner 的说明模板。
- `test-driven-development` 负责 task 内 TDD 纪律，不替代本协议。
- reviewer prompt 负责具体审查视角，不替代本协议的“可见性说明”。

## 失败信号

出现以下情况时，说明本协议没有被真正执行：

- implementer 已经开始改文件，但 Owner 没看到开始说明
- reviewer 已经被调用，但 Owner 没看到调用说明
- task 已被标记完成，但没有完成汇报
- 高风险任务直接写入，没有预览和确认环节
- 说明文本全是空泛套话，Owner 不能据此核对行为
