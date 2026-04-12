"""
Agent Lifecycle Tools
Agent 生命周期管理工具：支持 Agent 休眠、唤醒和状态查询
"""
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

from src.core.agent_lifecycle import get_lifecycle_manager, AgentState
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


def register_lifecycle_tools(server: Server) -> None:
    """注册生命周期工具到 MCP 服务器"""

    async def handle_put_agent_to_sleep(arguments: dict[str, Any]) -> list[TextContent]:
        """让 Agent 进入休眠状态"""
        try:
            role = arguments["role"]
            task_id = arguments["task_id"]
            wake_up_condition = arguments.get("wake_up_condition")
            timeout = arguments.get("timeout")

            manager = get_lifecycle_manager()

            # 确保 manager 已启动
            if not manager._running:
                await manager.start()

            result = await manager.put_agent_to_sleep(
                role=role,
                task_id=task_id,
                wake_up_condition=wake_up_condition,
                timeout=timeout
            )

            return [TextContent(
                type="text",
                text=f"""# Agent Sleep Protocol Initiated

## Agent: {result['state'].upper()}
## Role: {role.capitalize()}
## Task: {result['task_id']}

### Sleep Configuration
- **Wake-up Condition**: {result.get('wake_up_condition', 'None (manual wake-up)')}
- **Timeout**: {result.get('timeout', 'No timeout')} seconds

### Instructions for {role.capitalize()} Agent
You are now entering **SLEEP MODE**. This means:

1. **Stop Working**: Do not generate any more code or changes for this task
2. **Wait Patiently**: Wait for the wake-up condition to be met
3. **Preserve Context**: Keep your current context and state intact
4. **Be Ready**: You will be woken up when the condition is met

### What Happens Next
- **If you're Builder**: Wait for Reviewer to complete review
- **If you're Reviewer**: Wait for Owner to make decision
- **If you're Owner**: Wait for deployment confirmation

### Wake-Up Commands
When ready, use:
```
wake_up_agent(role="{role}", task_id="{task_id}")
```

---
**IMPORTANT**: Do NOT proceed with any new work until you are woken up.
This ensures proper agent coordination and prevents conflicts.
"""
            )]
        except Exception as e:
            logger.exception(f"Error in put_agent_to_sleep: {e}")
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    async def handle_wake_up_agent(arguments: dict[str, Any]) -> list[TextContent]:
        """唤醒休眠的 Agent"""
        try:
            role = arguments["role"]
            task_id = arguments["task_id"]
            reason = arguments.get("reason", "manual_wake_up")

            manager = get_lifecycle_manager()
            success = await manager.wake_up_agent(role, task_id, reason)

            if success:
                return [TextContent(
                    type="text",
                    text=f"""# Agent Woken Up

## Agent: {role.upper()}
## Task: {task_id}
## Reason: {reason}

### You Are Now ACTIVE
You have been woken up from sleep mode. You can now:

1. **Resume Work**: Continue with your next task
2. **Check Status**: Use `get_agent_status` to see your current state
3. **Proceed**: Move forward with your workflow

### Next Steps
- **If you're Builder**: Review the feedback and make necessary changes
- **If you're Reviewer**: Proceed with reviewing assigned tasks
- **If you're Owner**: Make your Go/No-Go decision

---
**Welcome back! You are now active and ready to continue.**
"""
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Failed to wake up {role} agent. It may not be sleeping."
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
                        AgentState.SLEEPING: "😴 **Sleeping** - Waiting for wake-up signal"
                    }

                    response += f"### Status Description\n{state_descriptions.get(current_state, 'Unknown state')}\n\n"

                    if current_state == AgentState.SLEEPING:
                        response += """### Sleep Mode Active
This agent is currently sleeping and will not perform any actions
until woken up by the appropriate trigger or manually.

Use `wake_up_agent` to wake this agent when ready.
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

    async def handle_get_agent_event_history(arguments: dict[str, Any]) -> list[TextContent]:
        """获取 Agent 事件历史"""
        try:
            role = arguments["role"]
            task_id = arguments.get("task_id")
            limit = arguments.get("limit", 50)

            manager = get_lifecycle_manager()

            if not manager._running:
                await manager.start()

            agent = manager.get_agent(role)
            events = agent.get_event_history(task_id=task_id, limit=limit)

            if not events:
                return [TextContent(
                    type="text",
                    text=f"No event history found for {role} agent" +
                    (f" and task {task_id}" if task_id else "")
                )]

            response = f"# Agent Event History: {role.upper()}\n\n"
            response += "## Recent Events\n\n"

            for event in reversed(events[-20:]):  # 显示最近 20 个事件
                response += f"### {event.state.value.upper()} - {event.task_id}\n"
                response += f"**Time**: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"

                if event.metadata:
                    response += "**Details**:\n"
                    for key, value in event.metadata.items():
                        response += f"- {key}: {value}\n"
                response += "\n"

            return [TextContent(type="text", text=response)]

        except Exception as e:
            logger.exception(f"Error in get_agent_event_history: {e}")
            return [TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]

    # 注册所有工具
    register_tool(server, Tool(
        name="put_agent_to_sleep",
        description="Put an agent to sleep after completing a task",
        inputSchema={
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["builder", "reviewer", "owner"],
                    "description": "Agent role to put to sleep"
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
                    "description": "Timeout in seconds (optional)"
                }
            },
            "required": ["role", "task_id"]
        }
    ), handle_put_agent_to_sleep)

    register_tool(server, Tool(
        name="wake_up_agent",
        description="Wake up a sleeping agent",
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

    register_tool(server, Tool(
        name="get_agent_event_history",
        description="Get the event history for an agent",
        inputSchema={
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["builder", "reviewer", "owner"],
                    "description": "Agent role"
                },
                "task_id": {
                    "type": "string",
                    "description": "Filter by task ID (optional)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of events to return (default: 50)"
                }
            },
            "required": ["role"]
        }
    ), handle_get_agent_event_history)

    logger.info("Registered agent lifecycle tools")
