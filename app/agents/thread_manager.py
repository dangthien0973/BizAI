from azure.ai.agents.models import MessageRole
from app.agents.agent_factory import get_ai_client

# Cache thread_id theo session_id
# session_id: chuỗi random do frontend tạo, đại diện cho 1 người dùng
# Phase 1: in-memory — mất khi restart server
# Phase 3: lưu vào bảng conversations trong DB
_thread_cache: dict[str, str] = {}


def get_or_create_thread(session_id: str) -> str:
    """
    Lấy thread_id từ cache hoặc tạo mới.
    Thread = lịch sử hội thoại — agent dùng để nhớ context.
    """
    if session_id not in _thread_cache:
        client = get_ai_client()

        # Tạo thread trống trên Azure
        # thread tồn tại trên Azure, có thể chứa nhiều message
        thread = client.threads.create()
        _thread_cache[session_id] = thread.id
        print(f"Created thread for session '{session_id}': {thread.id}")

    return _thread_cache[session_id]


async def send_message(
    agent_id: str,
    thread_id: str,
    user_message: str,
    tools_context: dict,  # thông tin thêm để truyền vào tools (tenant_id, db session...)
) -> str:
    """
    Gửi message vào thread, chạy agent, trả về reply.

    Flow:
    1. Thêm message của user vào thread
    2. Chạy agent (create_and_process_run) — agent đọc thread, quyết định gọi tool nào
    3. Tool chạy, kết quả trả về agent
    4. Agent tổng hợp và trả lời
    5. Đọc message cuối cùng của agent và trả về
    """
    client = get_ai_client()

    # Bước 1: thêm message user vào thread
    client.messages.create(
        thread_id=thread_id,
        role=MessageRole.USER,
        content=user_message,
    )

    # Bước 2 + 3 + 4: chạy agent
    # create_and_process tự xử lý vòng lặp tool calls
    # nếu agent cần gọi tool → gọi → nhận kết quả → tiếp tục
    # cho đến khi agent trả lời xong mới return
    run = client.runs.create_and_process(
        thread_id=thread_id,
        agent_id=agent_id,
    )

    # Kiểm tra run có thành công không
    if run.status == "failed":
        print(f"Run failed: {run.last_error}")
        return "Xin lỗi, tôi đang gặp sự cố. Vui lòng thử lại."

    # Bước 5: lấy message mới nhất của agent
    # list() trả về theo thứ tự mới nhất trước
    messages = client.messages.list(thread_id=thread_id)

    for msg in messages:
        # Tìm message đầu tiên có role ASSISTANT
        if msg.role == MessageRole.AGENT:
            # content là list — lấy phần text đầu tiên
            if msg.content and len(msg.content) > 0:
                return msg.content[0].text.value

    return "Xin lỗi, tôi không thể xử lý yêu cầu này."