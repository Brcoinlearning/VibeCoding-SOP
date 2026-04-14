#!/usr/bin/env python3
"""
需求分析阶段多 Agent 调度器

核心实现：将需求分析阶段拆分为多个独立 Agent 执行，避免上下文累积
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional
from filelock import FileLock


class RequirementsPhaseDispatcher:
    """需求分析阶段调度器"""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.evidence_dir = self.workspace / "10-requirements"
        self.planning_dir = self.workspace / "20-planning"
        self.state_dir = self.workspace / ".sop_state"

        # 确保目录存在
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.planning_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    async def dispatch_stage(
        self,
        task_id: str,
        stage_id: str,
        input_data: Dict,
        api_key: Optional[str] = None
    ) -> Dict:
        """
        分发任务到对应的子 Agent

        Args:
            task_id: 任务ID
            stage_id: 阶段ID (req-boundary, req-architecture, req-contract)
            input_data: 输入数据
            api_key: LLM API 密钥

        Returns:
            子 Agent 的执行结果
        """
        stage_dispatch = {
            "req-boundary": self._dispatch_boundary_convergence,
            "req-architecture": self._dispatch_architecture_decomposition,
            "req-contract": self._dispatch_contract_solidification,
        }

        if stage_id not in stage_dispatch:
            return {
                "success": False,
                "error": f"未知阶段: {stage_id}",
                "stage_id": stage_id
            }

        # 执行对应的子 Agent
        result = await stage_dispatch[stage_id](
            task_id=task_id,
            input_data=input_data,
            api_key=api_key
        )

        return result

    async def _dispatch_boundary_convergence(
        self,
        task_id: str,
        input_data: Dict,
        api_key: Optional[str] = None
    ) -> Dict:
        """
        阶段1：边界收敛
        调用 reverse-interviewing 子 Agent
        """
        # 这里可以调用独立的 LLM API 来执行边界收敛
        # 或者调用现有的 Skill

        system_prompt = """你是需求分析专家，负责边界收敛阶段。

你的任务：
1. 理解用户的原始需求
2. 通过深度提问消除模糊地带
3. 产出《业务规则备忘录》

你需要关注的维度：
- 核心概念澄清
- 目标用户确认
- 核心价值确认
- 输入数据规格
- 输出数据规格
- 处理逻辑
- 用户操作
- 数据边界
- 用户边界
- 系统边界
- 环境边界
- 性能要求
- 安全要求
- 可用性要求
- 可扩展性要求

输出格式：JSON
"""

        user_prompt = f"""原始需求：{input_data.get('raw_requirement', '')}

请进行深度分析并产出《业务规则备忘录》。"""

        # 调用独立 LLM API
        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=api_key)
            response = await client.messages.create(
                model="claude-3-7-sonnet-20250219",
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=4096
            )

            # 解析结果
            result_text = response.content[0].text

            # 保存到文件
            output_file = self.evidence_dir / f"{task_id}-business_rules_memo.md"
            with FileLock(str(output_file) + ".lock"):
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"# 业务规则备忘录\n\n{result_text}")

            return {
                "success": True,
                "stage_id": "req-boundary",
                "task_id": task_id,
                "artifact_file": str(output_file),
                "summary": "边界收敛完成，业务规则备忘录已生成"
            }

        except Exception as e:
            return {
                "success": False,
                "stage_id": "req-boundary",
                "error": str(e)
            }

    async def _dispatch_architecture_decomposition(
        self,
        task_id: str,
        input_data: Dict,
        api_key: Optional[str] = None
    ) -> Dict:
        """
        阶段2：架构拆解
        调用 architecture-patterns 子 Agent
        """
        # 读取前一阶段的产物
        business_rules_file = self.evidence_dir / f"{task_id}-business_rules_memo.md"
        if not business_rules_file.exists():
            return {
                "success": False,
                "stage_id": "req-architecture",
                "error": "业务规则备忘录不存在，请先完成边界收敛阶段"
            }

        with open(business_rules_file, "r", encoding="utf-8") as f:
            business_rules = f.read()

        system_prompt = """你是架构设计专家，负责架构拆解阶段。

你的任务：
1. 分析业务规则备忘录
2. 选择合适的架构模式（Clean Architecture, Hexagonal Architecture, DDD等）
3. 进行领域建模和分层设计
4. 拆解任务并创建执行计划

输出格式：JSON
"""

        user_prompt = f"""业务规则备忘录：

{business_rules}

请进行架构设计并产出：
1. 架构设计文档
2. Task 执行列表"""

        # 调用独立 LLM API
        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=api_key)
            response = await client.messages.create(
                model="claude-3-7-sonnet-20250219",
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=4096
            )

            result_text = response.content[0].text

            # 保存到文件
            output_file = self.planning_dir / f"{task_id}-architecture_design.md"
            with FileLock(str(output_file) + ".lock"):
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"# 架构设计文档\n\n{result_text}")

            return {
                "success": True,
                "stage_id": "req-architecture",
                "task_id": task_id,
                "artifact_file": str(output_file),
                "summary": "架构拆解完成，架构设计文档已生成"
            }

        except Exception as e:
            return {
                "success": False,
                "stage_id": "req-architecture",
                "error": str(e)
            }

    async def _dispatch_contract_solidification(
        self,
        task_id: str,
        input_data: Dict,
        api_key: Optional[str] = None
    ) -> Dict:
        """
        阶段3：契约固化
        调用 tdd 子 Agent
        """
        # 读取前一阶段的产物
        architecture_file = self.planning_dir / f"{task_id}-architecture_design.md"
        if not architecture_file.exists():
            return {
                "success": False,
                "stage_id": "req-contract",
                "error": "架构设计文档不存在，请先完成架构拆解阶段"
            }

        with open(architecture_file, "r", encoding="utf-8") as f:
            architecture_design = f.read()

        system_prompt = """你是测试驱动开发专家，负责契约固化阶段。

你的任务：
1. 分析架构设计文档
2. 识别关键验收场景
3. 编写 Gherkin 测试用例
4. 产出测试契约

输出格式：JSON
"""

        user_prompt = f"""架构设计文档：

{architecture_design}

请进行契约固化并产出：
1. Gherkin 测试用例
2. 测试契约文档"""

        # 调用独立 LLM API
        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=api_key)
            response = await client.messages.create(
                model="claude-3-7-sonnet-20250219",
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=4096
            )

            result_text = response.content[0].text

            # 保存到文件
            output_file = self.planning_dir / f"{task_id}-test_contract.md"
            with FileLock(str(output_file) + ".lock"):
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"# 测试契约文档\n\n{result_text}")

            return {
                "success": True,
                "stage_id": "req-contract",
                "task_id": task_id,
                "artifact_file": str(output_file),
                "summary": "契约固化完成，测试契约文档已生成"
            }

        except Exception as e:
            return {
                "success": False,
                "stage_id": "req-contract",
                "error": str(e)
            }


async def dispatch_requirements_phase(
    task_id: str,
    raw_requirement: str,
    workspace: str = ".",
    api_key: Optional[str] = None
) -> Dict:
    """
    执行完整的需求分析阶段（多 Agent 调度）

    Args:
        task_id: 任务ID
        raw_requirement: 原始需求
        workspace: 工作目录
        api_key: LLM API 密钥

    Returns:
        执行结果
    """
    dispatcher = RequirementsPhaseDispatcher(workspace)

    # 阶段1：边界收敛
    print(f"[{task_id}] 开始阶段1：边界收敛")
    result1 = await dispatcher.dispatch_stage(
        task_id=task_id,
        stage_id="req-boundary",
        input_data={"raw_requirement": raw_requirement},
        api_key=api_key
    )
    if not result1["success"]:
        return result1
    print(f"[{task_id}] 阶段1完成：{result1['summary']}")

    # 阶段2：架构拆解
    print(f"[{task_id}] 开始阶段2：架构拆解")
    result2 = await dispatcher.dispatch_stage(
        task_id=task_id,
        stage_id="req-architecture",
        input_data={},
        api_key=api_key
    )
    if not result2["success"]:
        return result2
    print(f"[{task_id}] 阶段2完成：{result2['summary']}")

    # 阶段3：契约固化
    print(f"[{task_id}] 开始阶段3：契约固化")
    result3 = await dispatcher.dispatch_stage(
        task_id=task_id,
        stage_id="req-contract",
        input_data={},
        api_key=api_key
    )
    if not result3["success"]:
        return result3
    print(f"[{task_id}] 阶段3完成：{result3['summary']}")

    return {
        "success": True,
        "task_id": task_id,
        "stages_completed": ["req-boundary", "req-architecture", "req-contract"],
        "artifacts": [
            result1["artifact_file"],
            result2["artifact_file"],
            result3["artifact_file"]
        ]
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="需求分析多 Agent 调度器")
    parser.add_argument("task_id")
    parser.add_argument("raw_requirement")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--api-key", default=None)

    args = parser.parse_args()

    result = asyncio.run(dispatch_requirements_phase(
        task_id=args.task_id,
        raw_requirement=args.raw_requirement,
        workspace=args.workspace,
        api_key=args.api_key
    ))

    print(json.dumps(result, ensure_ascii=False, indent=2))
