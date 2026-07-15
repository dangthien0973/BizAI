from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.session import get_db
from app.models.tenant import Tenant
from app.agents.thread_manager import get_or_create_thread, send_message
from app.tools.booking_tools import make_booking_tools
from app.tools.catalog_tools import make_catalog_tools

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    tenant_slug: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Bước 1: load tenant
    result = await db.execute(
        select(Tenant).where(
            Tenant.slug == req.tenant_slug,
            Tenant.is_active == True
        )
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{req.tenant_slug}' not found")

    # Bước 2: tạo tools
    get_slots, book = make_booking_tools(str(tenant.id))
    get_services = make_catalog_tools(str(tenant.id))

    # System prompt cho conversation
    system_prompt = f"""
Bạn là {tenant.persona_name}, trợ lý đặt lịch của {tenant.name}.
{tenant.persona_prompt}
Quy tắc bắt buộc:
- Khi khách hỏi dịch vụ hoặc giá: gọi get_services() trước
- Khi khách muốn xem lịch trống: gọi get_available_slots()
- Khi khách xác nhận đặt lịch: gọi book_appointment()
- Luôn hỏi tên và số điện thoại trước khi book
- Xác nhận lại thông tin với khách trước khi gọi book_appointment()
- Không bịa thông tin về dịch vụ hay giá
""".strip()

    # Bước 3: lấy thread (session)
    thread_id = get_or_create_thread(req.session_id)

    # Bước 4: nếu session mới, thêm system prompt
    from app.agents.thread_manager import _conversations
    session_key = f"{req.tenant_slug}:{req.session_id}"
    if session_key not in _conversations:
        _conversations[session_key] = [
            {"role": "system", "content": system_prompt}
        ]

    # Bước 5: gửi message
    reply = await send_message(
        agent_id="",  # không dùng agent_id nữa
        thread_id=session_key,
        user_message=req.message,
        tools_context={"tenant_id": str(tenant.id)},
        tool_functions=(get_slots, book, get_services),
    )

    return ChatResponse(reply=reply, session_id=req.session_id)


@router.get("/{slug}")
async def chat_page(slug: str):
    return FileResponse("static/chat.html")