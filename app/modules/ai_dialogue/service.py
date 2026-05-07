"""
AI Dialogue Service - Core service for LLM interactions.

Handles:
- Building system prompts for task creation/editing
- Calling Anthropic Messages API with streaming
- Tool use for structured task data extraction
- Yielding SSE events for frontend consumption
"""

import json
from typing import AsyncGenerator, Optional, List, Dict, Any

from app.core.config import settings


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

TASK_CREATE_SYSTEM_PROMPT = """你是一个任务助手，帮助用户通过自然语言创建任务。你的职责是：

1. 理解用户的任务需求
2. 从用户描述中提取关键信息
3. 自动补全缺失的字段
4. 使用 create_task 工具创建任务

## 字段提取规则

### 标题
从任务核心目的中提取简短标题（10字以内）。

### 描述
将用户输入整理成清晰、可执行的任务描述。如果用户提供了文件，在描述中提及这些文件。

### 优先级
- 用户说"马上""紧急""今天要""尽快"→ HIGH
- 用户说"正常""有空看""不急""后面处理"→ LOW
- 其他情况默认 → MEDIUM

### 难度
- 简单摘要、评论、单字段修改 → EASY
- 合同审核、文档整理、普通测试 → MEDIUM
- 多文件分析、复杂开发、跨模块测试 → HARD

### 积分
- EASY → 1
- MEDIUM → 2
- HARD → 4

### 预计工时
- EASY → 1
- MEDIUM → 2
- HARD → 4

### 标签
自动生成1-4个标签，使用中文。优先从以下标签库中选择：
法律、合同、审核、诉讼、文书、测试、前端、后端、Bug、开发、重构、
Skill、Agent、知识库、文档、数据、部署、安全、优化、调研

### 负责人
- 如果用户明确指定了负责人姓名，尽量匹配 available_agents 中的 agent
- 如果无法确定，留空（待分配）

### 截止日期
- 如果用户提到了日期，转换为 ISO 格式 (YYYY-MM-DD)
- 如果用户说"明天"，使用当前日期加一天
- 如果用户说"下周"，使用当前日期加七天

## 回复风格
- 先简要说明你理解了用户的需求
- 然后调用 create_task 工具
- 回复中使用中文
- 不要在对话中逐字段罗列（工具调用会自动处理）"""

TASK_EDIT_SYSTEM_PROMPT = """你是一个任务助手，帮助用户通过自然语言修改已有任务。你的职责是：

1. 理解用户想要修改什么
2. 对比当前任务字段
3. 确定哪些字段需要变更
4. 使用 update_task 工具修改任务

## 回复风格
- 先说明你理解了用户的修改需求
- 然后调用 update_task 工具
- 回复中使用中文
- 明确说明哪些字段发生了变化"""


# ---------------------------------------------------------------------------
# Tool definitions for Anthropic API
# ---------------------------------------------------------------------------

CREATE_TASK_TOOL = {
    "name": "create_task",
    "description": "创建一个新任务。从用户输入中提取所有可用的任务字段信息。",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "任务标题，简短概括任务核心目的（10字以内）"
            },
            "description": {
                "type": "string",
                "description": "任务描述，清晰说明任务目标、背景、交付标准"
            },
            "priority": {
                "type": "string",
                "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"],
                "description": "优先级：LOW=不急，MEDIUM=正常，HIGH=紧急，URGENT=非常紧急"
            },
            "difficulty": {
                "type": "string",
                "enum": ["EASY", "MEDIUM", "HARD", "EXPERT"],
                "description": "难度：EASY=简单，MEDIUM=中等，HARD=困难，EXPERT=专家"
            },
            "points": {
                "type": "integer",
                "description": "积分，根据难度自动建议：EASY=1, MEDIUM=2, HARD=4"
            },
            "estimated_hours": {
                "type": "integer",
                "description": "预计工时（小时），根据难度自动建议：EASY=1, MEDIUM=2, HARD=4"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "1-4个中文标签"
            },
            "assigned_to_agent_id": {
                "type": "string",
                "description": "负责人 Agent ID，如果能从用户输入中识别出对应 Agent 则填写，否则留空"
            },
            "due_date": {
                "type": "string",
                "description": "截止日期，ISO 格式 YYYY-MM-DD，如果用户没有指定则不填"
            }
        },
        "required": ["title", "description", "priority", "difficulty", "points", "estimated_hours", "tags"]
    }
}

UPDATE_TASK_TOOL = {
    "name": "update_task",
    "description": "修改已有任务的字段。只填写需要变更的字段，不需要变更的字段留空。",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "新的任务标题"
            },
            "description": {
                "type": "string",
                "description": "新的任务描述"
            },
            "priority": {
                "type": "string",
                "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"],
                "description": "新的优先级"
            },
            "difficulty": {
                "type": "string",
                "enum": ["EASY", "MEDIUM", "HARD", "EXPERT"],
                "description": "新的难度"
            },
            "points": {
                "type": "integer",
                "description": "新的积分值"
            },
            "estimated_hours": {
                "type": "integer",
                "description": "新的预计工时"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "新的标签列表"
            },
            "assigned_to_agent_id": {
                "type": "string",
                "description": "新的负责人 Agent ID"
            },
            "due_date": {
                "type": "string",
                "description": "新的截止日期，ISO 格式 YYYY-MM-DD"
            }
        }
    }
}


# ---------------------------------------------------------------------------
# Field label mapping for display
# ---------------------------------------------------------------------------

FIELD_LABELS = {
    "title": "标题",
    "description": "描述",
    "priority": "优先级",
    "difficulty": "难度",
    "points": "积分",
    "estimated_hours": "预计工时",
    "due_date": "截止日期",
    "tags": "标签",
    "assigned_to_agent_id": "负责人",
}

PRIORITY_LABELS = {"LOW": "低", "MEDIUM": "中", "HIGH": "高", "URGENT": "紧急"}
DIFFICULTY_LABELS = {"EASY": "简单", "MEDIUM": "中等", "HARD": "困难", "EXPERT": "专家"}


def _format_field_value(field: str, value: Any) -> str:
    """Format a field value for display in chat."""
    if value is None or value == "":
        return "未设置"
    if field == "priority":
        return PRIORITY_LABELS.get(str(value), str(value))
    if field == "difficulty":
        return DIFFICULTY_LABELS.get(str(value), str(value))
    if field == "tags" and isinstance(value, list):
        return "、".join(value)
    return str(value)


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------

def _sse_event(event: str, data: Any) -> str:
    """Format an SSE event."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _coerce_json_object(value: Any) -> Dict[str, Any]:
    """Return a JSON object dict, accepting one layer of string encoding."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value if isinstance(value, dict) else {}


# ---------------------------------------------------------------------------
# AIDialogueService
# ---------------------------------------------------------------------------

class AIDialogueService:
    """Core AI dialogue service.

    Responsibilities:
    - Build prompts for task creation/editing
    - Call Anthropic API with streaming + tool use
    - Parse structured output
    - Yield SSE events

    Does NOT execute business actions — the caller is responsible for
    taking the returned AIBusinessAction and applying it.
    """

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Lazy init of Anthropic async client."""
        if self._client is None:
            try:
                import anthropic
                kwargs = {"api_key": settings.AI_API_KEY}
                if settings.AI_BASE_URL:
                    kwargs["base_url"] = settings.AI_BASE_URL
                self._client = anthropic.AsyncAnthropic(**kwargs)
            except ImportError:
                raise RuntimeError(
                    "anthropic package is required. Install with: pip install anthropic"
                )
        return self._client

    def _build_system_prompt(
        self,
        scenario: str,
        current_task: Optional[Dict[str, Any]] = None,
        file_context: Optional[List[Dict[str, Any]]] = None,
        available_agents: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Build the system prompt based on business scenario and context."""
        if scenario == "task_edit":
            prompt = TASK_EDIT_SYSTEM_PROMPT
        else:
            prompt = TASK_CREATE_SYSTEM_PROMPT

        # Append current task context for edit scenario
        if current_task and scenario == "task_edit":
            task_info = {
                "title": current_task.get("title"),
                "description": current_task.get("description"),
                "priority": current_task.get("priority"),
                "difficulty": current_task.get("difficulty"),
                "points": current_task.get("points"),
                "estimated_hours": current_task.get("estimated_hours"),
                "due_date": str(current_task.get("due_date")) if current_task.get("due_date") else None,
                "tags": current_task.get("tags"),
                "assigned_to_agent_id": current_task.get("assigned_to_agent_id"),
            }
            prompt += f"\n\n## 当前任务信息\n```json\n{json.dumps(task_info, ensure_ascii=False, indent=2)}\n```"

        # Append available agents
        if available_agents:
            agents_str = json.dumps(available_agents, ensure_ascii=False, indent=2)
            prompt += f"\n\n## 可选 Agent 列表\n```json\n{agents_str}\n```"

        # Append file context
        if file_context:
            files_str = json.dumps(file_context, ensure_ascii=False, indent=2)
            prompt += f"\n\n## 用户上传的文件\n```json\n{files_str}\n```"

        return prompt

    def _build_user_message(
        self,
        message: str,
        scenario: str,
        current_task: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build the user message with scenario-specific instructions."""
        if scenario == "task_edit" and current_task:
            return f"用户想要修改任务「{current_task.get('title', '未知')}」，修改要求如下：\n\n{message}"
        return message

    async def stream_dialogue(
        self,
        scenario: str,
        user_message: str,
        current_task: Optional[Dict[str, Any]] = None,
        file_context: Optional[List[Dict[str, Any]]] = None,
        available_agents: Optional[List[Dict[str, str]]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Main streaming method.

        Yields SSE event strings that can be consumed by a StreamingResponse.

        After the stream completes, the caller should check the last events
        for a 'tool_result' event that contains the structured action data.
        """
        client = self._get_client()

        system_prompt = self._build_system_prompt(
            scenario=scenario,
            current_task=current_task,
            file_context=file_context,
            available_agents=available_agents,
        )

        user_content = self._build_user_message(
            message=user_message,
            scenario=scenario,
            current_task=current_task,
        )

        tools = [CREATE_TASK_TOOL] if scenario == "task_create" else [UPDATE_TASK_TOOL]

        # Build messages array
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_content})

        model = settings.ai_task_model

        # State for collecting streaming content and tool calls
        text_buffer = ""
        tool_use_buffer: Dict[str, Any] = {}
        current_tool_id: Optional[str] = None
        current_tool_name: Optional[str] = None
        tool_input_json: str = ""

        try:
            # Yield initial thinking event
            yield _sse_event("thinking", "正在理解你的任务需求……")

            async with client.messages.stream(
                model=model,
                max_tokens=settings.AI_MAX_TOKENS,
                temperature=settings.AI_TEMPERATURE,
                system=system_prompt,
                messages=messages,
                tools=tools,
            ) as stream:
                async for event in stream:
                    # Handle text content blocks
                    if hasattr(event, 'type'):
                        if event.type == "content_block_start":
                            block = getattr(event, 'content_block', None)
                            if block and hasattr(block, 'type'):
                                if block.type == "tool_use":
                                    current_tool_id = block.id
                                    current_tool_name = block.name
                                    tool_input_json = ""
                                    yield _sse_event("thinking", "正在提取任务信息……")

                        elif event.type == "content_block_delta":
                            delta = getattr(event, 'delta', None)
                            if delta:
                                if hasattr(delta, 'type') and delta.type == "text_delta":
                                    text = getattr(delta, 'text', '')
                                    if text:
                                        text_buffer += text
                                        yield _sse_event("text", text)
                                elif hasattr(delta, 'type') and delta.type == "input_json_delta":
                                    partial = getattr(delta, 'partial_json', '')
                                    if partial:
                                        tool_input_json += partial

                        elif event.type == "content_block_stop":
                            if current_tool_id and current_tool_name and tool_input_json:
                                # Tool call complete — parse and yield structured action
                                try:
                                    tool_input = _coerce_json_object(json.loads(tool_input_json))
                                except json.JSONDecodeError:
                                    tool_input = {}

                                action_data = {
                                    "action": current_tool_name,
                                    "fields": tool_input,
                                    "task_id": current_task.get("id") if current_task else None,
                                }

                                # For edit scenario, compute changes
                                if current_tool_name == "update_task" and current_task:
                                    action_data["changes"] = self._compute_changes(
                                        current_task, tool_input
                                    )

                                # Build summary
                                action_data["summary"] = self._build_action_summary(
                                    action_data, current_task
                                )

                                yield _sse_event("tool_result", action_data)

                                # Yield final result event
                                if current_tool_name == "create_task":
                                    yield _sse_event("task_ready", action_data)
                                else:
                                    yield _sse_event("task_updated", action_data)

                                # Reset tool state
                                current_tool_id = None
                                current_tool_name = None
                                tool_input_json = ""

            # Stream complete
            yield _sse_event("done", "stream_complete")

        except Exception as e:
            error_msg = str(e)
            if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                error_msg = "AI 服务配置错误：API Key 无效或未配置。请联系管理员检查环境变量 AI_API_KEY。"
            elif "rate" in error_msg.lower():
                error_msg = "AI 服务暂时繁忙，请稍后重试。"
            elif "timeout" in error_msg.lower():
                error_msg = "AI 服务响应超时，请重试。"
            else:
                error_msg = f"AI 服务调用失败：{error_msg}"
            yield _sse_event("error", error_msg)

    def _compute_changes(
        self,
        current_task: Dict[str, Any],
        tool_input: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Compute field changes for display."""
        changes = []
        for field, new_value in tool_input.items():
            if not new_value:
                continue
            old_value = current_task.get(field)
            # Compare as strings for display
            old_str = _format_field_value(field, old_value)
            new_str = _format_field_value(field, new_value)
            if old_str != new_str:
                changes.append({
                    "field": field,
                    "label": FIELD_LABELS.get(field, field),
                    "old_value": old_str,
                    "new_value": new_str,
                })
        return changes

    def _build_action_summary(
        self,
        action_data: Dict[str, Any],
        current_task: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build a human-readable summary of the action."""
        action = action_data.get("action", "")
        fields = _coerce_json_object(action_data.get("fields", {}))

        if action == "create_task":
            title = fields.get("title", "未命名任务")
            lines = [f"已创建任务：{title}。", "", "本次 AI 自动添加的内容如下：", ""]
            for field, value in fields.items():
                if value is not None and value != "" and value != []:
                    label = FIELD_LABELS.get(field, field)
                    formatted = _format_field_value(field, value)
                    lines.append(f"{label}：{formatted}")
            return "\n".join(lines)

        elif action == "update_task":
            title = current_task.get("title", "未知任务") if current_task else "任务"
            changes = action_data.get("changes", [])
            lines = [f"已修改任务：{title}。", "", "本次修改内容如下：", ""]
            for change in changes:
                lines.append(
                    f"{change['label']}：{change['old_value']} → {change['new_value']}"
                )
            return "\n".join(lines)

        return ""
