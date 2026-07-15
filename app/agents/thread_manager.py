import inspect
import json

from app.agents.agent_factory import get_ai_client
from app.core.config import get_settings

settings = get_settings()

# Lưu lịch sử hội thoại theo session_key ("tenant_slug:session_id")
# Phase 1: in-memory — mất khi restart server
# Phase 3: lưu vào bảng conversations trong DB
_conversations: dict[str, list[dict]] = {}


def get_or_create_thread(session_id: str) -> str:
    """Giữ lại tên hàm cũ để tương thích — thực chất chỉ trả về session_id làm khóa."""
    return session_id


def _to_tool_schema(func) -> dict:
    """Chuyển 1 hàm Python (docstring Google-style) thành function-calling schema."""
    sig = inspect.signature(func)
    doc = inspect.getdoc(func) or ""
    description = doc.split("Args:")[0].strip()

    properties = {}
    required = []
    for name in sig.parameters:
        properties[name] = {"type": "string"}
        required.append(name)

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


async def send_message(
    agent_id: str,
    thread_id: str,
    user_message: str,
    tools_context: dict,
    tool_functions: tuple,
) -> str:
    """
    Gửi message vào conversation, gọi Azure OpenAI chat completion,
    xử lý tool calls (nếu có), trả về reply cuối cùng.
    """
    client = get_ai_client()
    history = _conversations.setdefault(thread_id, [])
    history.append({"role": "user", "content": user_message})

    functions_by_name = {f.__name__: f for f in tool_functions}
    tool_schemas = [_to_tool_schema(f) for f in tool_functions]

    # Tối đa 5 vòng lặp tool call để tránh loop vô hạn
    for _ in range(5):
        response = client.chat.completions.create(
            model=settings.azure_ai_model,
            messages=history,
            tools=tool_schemas,
        )
        choice = response.choices[0]
        message = choice.message

        if not message.tool_calls:
            history.append({"role": "assistant", "content": message.content})
            return message.content or "Xin lỗi, tôi không thể xử lý yêu cầu này."

        history.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            }
        )

        for tc in message.tool_calls:
            func = functions_by_name.get(tc.function.name)
            if func is None:
                result = json.dumps({"error": f"Không tìm thấy tool '{tc.function.name}'"})
            else:
                args = json.loads(tc.function.arguments or "{}")
                result = func(**args)

            history.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )

    return "Xin lỗi, tôi đang gặp sự cố. Vui lòng thử lại."
