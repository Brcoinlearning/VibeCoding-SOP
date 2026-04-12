"""
Agent Blocking Sleep Tools
真正的睡眠/唤醒阻塞工具，替代提示式编排
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent

from mcp_server.tools.registry import register_tool

# 添加项目路径
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.agent_lifecycle_blocking import get_lifecycle_manager, AgentState
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


def register_blocking_tools(server: Server) -> None:
    """注册阻塞工具到 MCP 服务器"""

    async def handle_blocking_sleep(arguments: dict[str, Any]) -> list[TextContent]:
        """让 Agent 进入真正的阻塞睡眠"""
        try:
            role = arguments["role"]
            task_id = arguments["task_id"]
            wake_up_condition = arguments.get("wake_up_condition")
            timeout = arguments.get("timeout")

            manager = get_lifecycle_manager()

            # 确保 manager 已启动
            if not manager._running:
                await manager.start()

            # 获取 Agent 并进入阻塞睡眠
            agent = manager.get_agent(role)
            result = await agent.enter_blocking_sleep(
                task_id=task_id,
                wake_up_condition=wake_up_condition,
                timeout=timeout
            )

            if result["success"]:
                return [TextContent(
                    type="text",
                    text=f"""# Agent Entering BLOCKING Sleep

## Agent: {role.upper()}
## Task: {result['task_id']}
## State: SLEEPING (BLOCKING)

### ⚠️ IMPORTANT: BLOCKING MODE ACTIVE
You are now in **TRUE BLOCKING SLEEP**. This means:
- Your execution is **PAUSED** at this line
- You will **NOT proceed** until woken up
- No further code will be generated
- No further actions will be taken

### Wake-Up Condition
**Condition**: {result.get('wake_up_condition', 'Manual Wake-Up')}

### What To Expect
1. **DO NOT** generate any more code
2. **DO NOT** start new tasks
3. **WAIT** for the wake-up signal
4. **RESUME** when you receive "Wake-Up" notification

### How Wake-Up Works
You will be automatically woken up when:
- The wake-up condition is met (e.g., "review_completed")
- Another agent manually wakes you up
- Timeout expires (if set)

### Technical Details
```
Blocking Mechanism: asyncio.ConditionVariable
Task ID: {task_id}
Agent Role: {role}
Start Time: {datetime.now().isoformat()}
```

---
**NOTE**: This is a real blocking operation. You cannot bypass this.
Use `wake_up_agent` tool to wake this agent when ready.
"""
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"""# Sleep Failed

## Agent: {role.upper()}
## Task: {task_id}
## Reason: {result.get('reason', 'unknown')}

### What Happened
The sleep operation could not be completed:
- **Reason**: {result.get('reason', 'Unknown')}
- **Task ID**: {task_id}

### Next Steps
1. Check the error reason above
2. Decide how to proceed
3. You may need to retry or take alternative action
"""
                )]

        except Exception as e:
            logger.exception(f"Error in blocking_sleep: {e}")
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def handle_wait_for_review(arguments: dict[str, Any]) -> list[TextContent]:
        """Builder Agent 等待审查完成（阻塞）"""
        try:
            task_id = arguments["task_id"]
            timeout = arguments.get("timeout")

            manager = get_lifecycle_manager()

            if not manager._running:
                await manager.start()

            agent = manager.get_agent("builder")
            result = await agent.wait_for_review_complete(
                task_id=task_id,
                timeout=timeout
            )

            if result["success"]:
                review_result = result.get("review_result", {})

                return [TextContent(
                    type="text",
                    text=f"""# Review Completed - Agent Woken Up

## Task: {task_id}
## Your Sleep Has Ended

You were woken up because the review is complete!

### Review Results

```json
{review_result}
```

### What To Do Next

1. **Review the feedback** above
2. **Make necessary changes** based on review findings
3. **Re-submit** if needed
4. **Or proceed** if approved

### Blocking Details
- **Original Task**: {task_id}
- **Wake-Up Reason**: review_completed
- **Agent State**: ACTIVE (no longer sleeping)

---
**You are now awake and ready to continue work.**
"""
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"""# Wait Failed

## Task: {task_id}
## Reason: {result.get('reason', 'unknown')}

### What Happened
The waiting operation could not be completed:
- **Reason**: {result.get('reason', 'Unknown')}
- **Task ID**: {task_id}

### Next Steps
1. Check if review is actually complete
2. Use `get_agent_status` to check current state
3. Decide how to proceed
"""
                )]

        except Exception as e:
            logger.exception(f"Error in wait_for_review: {e}")
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def handle_wait_for_decision(arguments: dict[str, Any]) -> list[TextContent]:
        """Agent 等待 Owner 决策（阻塞）"""
        try:
            task_id = arguments["task_id"]
            timeout = arguments.get("timeout")

            manager = get_lifecycle_manager()

            if not manager._running:
                await manager.start()

            # 根据调用者角色决定使用哪个 Agent
            # 这里简化处理，默认使用 Builder
            agent = manager.get_agent("builder")
            result = await agent.wait_for_decision(
                task_id=task_id,
                timeout=timeout
            )

            if result["success"]:
                decision = result.get("decision", "proceed")

                return [TextContent(
                    type="text",
                    text=f"""# Decision Received - Agent Woken Up

## Task: {task_id}
## Your Sleep Has Ended

Owner has made a decision!

### Decision: {decision.upper()}

### What To Do Next

**IF APPROVED (GO)**:
- Your changes are approved
- You can proceed with next steps
- Consider the task complete

**IF REJECTED (NO-GO)**:
- Review the rejection reasons
- Make required changes
- Re-submit for review

**IF CONDITIONAL**:
- Address the conditions first
- Re-submit for review

### Blocking Details
- **Original Task**: {task_id}
- **Wake-Up Reason**: owner_decision
- **Agent State**: ACTIVE (no longer sleeping)

---
**You are now awake and ready to proceed.**
"""
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"""# Wait Failed

## Task: {task_id}
## Reason: {result.get('reason', 'unknown')}

### What Happened
The waiting operation could not be completed:
- **Reason**: {result.get('reason', 'Unknown')}
- **Task ID**: {task_id}

### Next Steps
1. Check if decision is ready
2. Use `get_agent_status` to check current state
3. Decide how to proceed
"""
                )]

        except Exception as e:
            logger.exception(f"Error in wait_for_decision: {e}")
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def handle_wake_up_agent(arguments: dict[str, Any]) -> list[TextContent]:
        """唤醒阻塞的 Agent"""
        try:
            role = arguments["role"]
            task_id = arguments["task_id"]
            reason = arguments.get("reason", "manual_wake_up")

            manager = get_lifecycle_manager()
            success = await manager.wake_up_agent(role, task_id, reason)

            if success:
                return [TextContent(
                    type="text",
                    text=f"""# Agent Woken Up Successfully

## Agent: {role.upper()}
## Task: {task_id}
## Reason: {reason}

### Wake-Up Confirmed ✅
The agent has been successfully woken up and can now:
- Resume work
- Check status
- Process next tasks

### Agent State
```
Current State: ACTIVE
Previous State: SLEEPING
Task: {task_id}
```

---
**Agent is now active and ready to continue.**
"""
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"""# Wake-Up Failed

## Agent: {role.upper()}
## Task: {task_id}

### Could Not Wake Up
The agent could not be woken up. Possible reasons:
- Agent is not sleeping
- Task ID mismatch
- Agent is in error state

### Recommendation
Use `get_agent_status` to check the current state of the agent.
"""
                )]

        except Exception as e:
            logger.exception(f"Error in wake_up_agent: {e}")
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def handle_get_agent_status(arguments: dict[str, Any]) -> list[TextContent]:
        """获取 Agent 状态"""
        try:
            role = arguments.get("role")

            manager = get_lifecycle_manager()

            if not manager._running:
                await manager.start()

            if role:
                # 获取单个 Agent 状态
                try:
                    agent = manager.get_agent(role)
                    current_state = agent.get_state()
                    current_task = agent.get_current_task()
                    is_sleeping = agent.is_sleeping()

                    response = f"""# Agent Status: {role.upper()}

## Current State: {current_state.value.upper()}

"""
                    if current_task:
                        response += f"### Current Task\n**Task ID**: {current_task}\n\n"

                    # 添加状态说明
                    state_descriptions = {
                        AgentState.IDLE: "✅ **Available** - Ready to accept new tasks",
                        AgentState.WORKING: "⚙️ **Working** - Currently processing a task",
                        AgentState.WAITING: "⏳ **Waiting** - Waiting for other agents",
                        AgentState.BLOCKED: "🚫 **Blocked** - Blocked, waiting for resolution",
                        AgentState.COMPLETED: "✅ **Completed** - Task completed successfully",
                        AgentState.ERROR: "❌ **Error** - An error has occurred",
                        AgentState.SLEEPING: "😴 **Sleeping (BLOCKING)** - Execution paused, waiting for wake-up"
                    }

                    response += f"### Status Description\n{state_descriptions.get(current_state, 'Unknown state')}\n\n"

                    if is_sleeping:
                        response += """### ⚠️ BLOCKING MODE ACTIVE
This agent is currently in TRUE BLOCKING SLEEP.
- Execution is PAUSED
- Agent is waiting for wake-up signal
- Use `wake_up_agent` to wake this agent

**IMPORTANT**: Do not start new work until this agent is woken up.
"""

                    return [TextContent(type="text", text=response)]

                except ValueError:
                    return [TextContent(
                        type="text",
                        text=f"Error: Unknown agent role '{role}'"
                    )]
            else:
                # 获取所有 Agent 状态
                states = manager.get_agent_states()

                response = "# All Agent Status\n\n"
                response += "| Agent | State |\n"
                response += "|-------|-------|\n"

                state_icons = {
                    "idle": "✅",
                    "working": "⚙️",
                    "waiting": "⏳",
                    "blocked": "🚫",
                    "completed": "✅",
                    "error": "❌",
                    "sleeping": "😴"
                }

                for role, state in states.items():
                    icon = state_icons.get(state, "❓")
                    response += f"| {icon} {role.capitalize()} | {state.upper()} |\n"

                response += f"\n**Timestamp**: {datetime.now().isoformat()}"

                return [TextContent(type="text", text=response)]

        except Exception as e:
            logger.exception(f"Error in get_agent_status: {e}")
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    # 注册所有工具
    register_tool(server, Tool(
        name="blocking_sleep",
        description="TRUE BLOCKING SLEEP - Put agent to sleep until woken up",
        inputSchema={
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["builder", "reviewer", "owner"],
                    "description": "Agent role to put to blocking sleep"
                },
                "task_id": {
                    "type": "string",
                    "description": "Current task ID"
                },
                "wake_up_condition": {
                    "type": "string",
                    "description": "Condition that will wake up the agent (optional)"
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (optional, null = infinite)"
                }
            },
            "required": ["role", "task_id"]
        }
    ), handle_blocking_sleep)

    register_tool(server, Tool(
        name="wait_for_review",
        description="Wait for review completion (BLOCKING) - Builder waits until review is done",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID"
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (optional, null = infinite)"
                }
            },
            "required": ["task_id"]
        }
    ), handle_wait_for_review)

    register_tool(server, Tool(
        name="wait_for_decision",
        description="Wait for owner decision (BLOCKING) - Wait until Go/No-Go decision",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID"
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (optional, null = infinite)"
                }
            },
            "required": ["task_id"]
        }
    ), handle_wait_for_decision)

    register_tool(server, Tool(
        name="wake_up_agent",
        description="Wake up a sleeping agent - Releases blocking sleep",
        inputSchema={
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["builder", "reviewer", "owner"],
                    "description": "Agent role to wake up"
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for waking up (optional)"
                }
            },
            "required": ["role", "task_id"]
        }
    ), handle_wake_up_agent)

    register_tool(server, Tool(
        name="get_agent_status",
        description="Get the current status of agents",
        inputSchema={
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["builder", "reviewer", "owner"],
                    "description": "Agent role (optional, if not provided returns all agents)"
                }
            }
        }
    ), handle_get_agent_status)

    logger.info("Registered agent blocking tools (TRUE blocking sleep implemented)")
