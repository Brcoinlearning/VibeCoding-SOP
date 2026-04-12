# MCP Server Refactoring - Quick Start Guide

## Overview

This guide helps you quickly get started with the refactored MCP Server architecture.

## Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt
```

## Starting the MCP Server

The MCP Server now starts with all event-driven components automatically:

```bash
cd orchestrator
python -m mcp_server.mcp_server_main
```

**What happens on startup**:
1. EventBus starts processing events
2. ContextQueueManager starts managing agent queues
3. BackgroundListenerManager starts monitoring:
   - Git repository for new commits
   - File system for test results

## Basic Usage

### 1. Publishing Events

#### Publish Build Event
```python
from mcp_server.adapters.event_publisher import get_event_publisher

publisher = get_event_publisher()
result = await publisher.publish_build_event(
    task_id="T-102",
    commit_hash="abc123def",
    branch="feature/new-feature",
    diff_summary="3 files changed, 50 insertions(+)",
    changed_files=["src/main.py", "tests/test_main.py"],
    wait_for_processing=True,
    timeout=30.0
)
```

#### Publish Test Event
```python
result = await publisher.publish_test_event(
    task_id="T-102",
    passed=True,
    total_tests=150,
    failed_tests=0,
    test_summary="All tests passed",
    coverage_percent=87.5,
    wait_for_processing=True
)
```

### 2. Using Context Queues

#### Builder Agent - Route Evidence to Reviewer
```python
from src.core.context_queue import get_context_queue_manager

manager = get_context_queue_manager()

# Route evidence for review
await manager.route_to_reviewer(
    task_id="T-102",
    evidence={
        "commit_hash": "abc123",
        "diff": "+ new code here",
        "test_results": {"passed": True, "total": 100}
    },
    metadata={"priority": "high", "author": "builder-agent"}
)
```

#### Reviewer Agent - Get and Process Tasks
```python
# Get next task
task = await manager.get_reviewer_input(timeout=30.0)

if task:
    print(f"Reviewing task: {task.task_id}")
    print(f"Evidence: {task.content}")

    # Process evidence...

    # Submit review result
    await manager.submit_review(
        task_id=task.task_id,
        review_result={
            "decision": "approved",
            "overall_score": 95,
            "findings": []
        },
        reviewer_id="reviewer-agent-1"
    )
```

#### Owner Agent - Get Review Results
```python
# Get next review result
result = await manager.get_owner_input(timeout=30.0)

if result:
    print(f"Task: {result.task_id}")
    print(f"Reviewer: {result.metadata['reviewer_id']}")
    print(f"Decision: {result.content['decision']}")

    # Make Go/No-Go decision...
```

### 3. Monitoring Queue Status

```python
# Get status of all queues
sizes = manager.get_all_queue_sizes()
print(f"Builder queue: {sizes['builder']}")
print(f"Reviewer queue: {sizes['reviewer']}")
print(f"Owner queue: {sizes['owner']}")
```

## MCP Tool Usage

When using the MCP Server through the MCP protocol, tools are available:

### get_reviewer_task
```json
{
  "tool": "get_reviewer_task",
  "arguments": {
    "task_id": "T-102",
    "timeout": 30.0
  }
}
```

### submit_review
```json
{
  "tool": "submit_review",
  "arguments": {
    "task_id": "T-102",
    "review_result": {
      "decision": "approved",
      "overall_score": 95,
      "findings": []
    },
    "reviewer_id": "reviewer-1"
  }
}
```

### get_queue_status
```json
{
  "tool": "get_queue_status",
  "arguments": {}
}
```

### route_evidence
```json
{
  "tool": "route_evidence",
  "arguments": {
    "task_id": "T-102",
    "evidence": {
      "commit": "abc123",
      "diff": "+ new code"
    }
  }
}
```

## Complete Workflow Example

Here's a complete example of the Builder → Reviewer → Owner workflow:

```python
import asyncio
from src.core.context_queue import get_context_queue_manager
from src.core.event_bus import get_event_bus

async def complete_workflow():
    # Initialize
    event_bus = get_event_bus()
    queue_manager = get_context_queue_manager()

    await event_bus.start()
    await queue_manager.start()

    try:
        # === BUILDER AGENT ===
        print("Builder: Creating evidence...")

        # Capture git changes (simulated)
        evidence = {
            "task_id": "T-DEMO-001",
            "commit_hash": "abc123",
            "branch": "feature/demo",
            "diff": "+ print('Hello, World!')",
            "test_results": {
                "passed": True,
                "total": 10,
                "failed": 0
            }
        }

        # Route to Reviewer
        await queue_manager.route_to_reviewer(
            task_id=evidence["task_id"],
            evidence=evidence
        )
        print("Builder: Evidence routed to Reviewer")

        # === REVIEWER AGENT ===
        print("\nReviewer: Waiting for task...")

        # Get task
        task = await queue_manager.get_reviewer_input(timeout=5.0)
        if not task:
            print("Reviewer: No task received")
            return

        print(f"Reviewer: Received task {task.task_id}")
        print(f"Reviewer: Reviewing {task.content['diff']}")

        # Review (simulated)
        review_result = {
            "decision": "approved",
            "overall_score": 100,
            "findings": [],
            "notes": "Code looks great!"
        }

        # Submit review
        await queue_manager.submit_review(
            task_id=task.task_id,
            review_result=review_result,
            reviewer_id="demo-reviewer"
        )
        print("Reviewer: Review submitted")

        # === OWNER AGENT ===
        print("\nOwner: Waiting for review result...")

        # Get review result
        result = await queue_manager.get_owner_input(timeout=5.0)
        if not result:
            print("Owner: No result received")
            return

        print(f"Owner: Received review for {result.task_id}")
        print(f"Owner: Decision: {result.content['decision']}")
        print(f"Owner: Score: {result.content['overall_score']}")

        # Make Go/No-Go decision
        if result.content['decision'] == 'approved':
            print("Owner: ✅ GO - Approved for deployment")
        else:
            print("Owner: ❌ NO-GO - Needs revision")

        # Notify Builder
        await queue_manager.route_notification(
            task_id=result.task_id,
            notification={
                "decision": "go",
                "message": "Approved for deployment"
            },
            to_role="builder",
            from_role="owner"
        )
        print("Owner: Decision routed to Builder")

    finally:
        await queue_manager.stop()
        await event_bus.stop()

# Run the workflow
asyncio.run(complete_workflow())
```

## Testing

### Run All Tests
```bash
pytest tests/mcp/ -v
```

### Run Specific Test Suite
```bash
# Event publisher tests
pytest tests/mcp/test_event_publisher.py -v

# Context queue tests
pytest tests/mcp/test_context_queue.py -v

# Async listener tests
pytest tests/mcp/test_async_listener.py -v

# End-to-end tests
pytest tests/mcp/test_e2e_isolation.py -v
```

### Run with Coverage
```bash
pytest tests/mcp/ -v --cov=src/core --cov=mcp_server --cov-report=html
```

## Configuration

Edit `src/config/settings.py` to customize:

```python
# Event Bus
enable_event_logging = True
event_processing_timeout = 30.0

# Context Queues
context_queue_max_size = 100
context_queue_persist_dir = base_path / ".context_queues"

# Background Listeners
git_poll_interval = 5.0
file_watch_patterns = {"pytest_results.json", "test-results.xml"}
```

## Troubleshooting

### Events Not Processing
```python
# Ensure EventBus is started
event_bus = get_event_bus()
await event_bus.start()
```

### Queues Filling Up
```python
# Increase queue size
manager = ContextQueueManager(max_queue_size=200)
```

### Git Listener Not Working
```bash
# Verify git repository
cd /path/to/repo
git status
```

### File Watcher Not Detecting Tests
```python
# Add your test file pattern
manager.add_file_watcher(
    watch_path=Path("."),
    test_patterns={"my_test_results.json"}
)
```

## Advanced Usage

### Custom Event Handlers
```python
from src.core.event_bus import get_event_bus
from src.models.events import BuildCompletedEvent

event_bus = get_event_bus()

async def my_handler(event: BuildCompletedEvent):
    print(f"Build completed: {event.commit_hash}")

event_bus.subscribe(EventType.BUILD_COMPLETED, my_handler)
```

### Custom Polling Intervals
```python
from src.core.async_listener import get_background_listener_manager

manager = get_background_listener_manager()

# Fast polling for development
manager.add_git_listener(
    repo_path=Path("."),
    poll_interval=1.0  # 1 second
)

# Slow polling for production
manager.add_git_listener(
    repo_path=Path("/path/to/prod"),
    poll_interval=60.0  # 1 minute
)
```

## Next Steps

1. **Read the full documentation**: `docs/MCP_ARCHITECTURE_REFACTORING.md`
2. **Explore the examples**: Check the test files for usage patterns
3. **Integrate with your agents**: Use the MCP tools in your agent workflows
4. **Monitor and tune**: Adjust polling intervals and queue sizes based on load

## Support

For issues or questions:
- Check the troubleshooting section in the main documentation
- Review the test files for examples
- Examine the source code documentation

---

**Last Updated**: 2025-01-12
**Version**: 1.0.0
