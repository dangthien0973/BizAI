from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.session import get_db
from app.models.tenant import Tenant
from app.agents.agent_factory import get_or_create_agent
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

    # Bước 2: tạo tools với tenant_id bên trong (closure)
    # tools dùng session đồng bộ riêng (SyncSessionLocal) — không dùng
    # AsyncSession của request vì Azure AgentsClient gọi tool function
    # đồng bộ, không await
    get_slots, book = make_booking_tools(str(tenant.id))
    get_services = make_catalog_tools(str(tenant.id))

    # Bước 3: lấy agent — truyền tools vào để tạo agent lần đầu
    agent_id = await get_or_create_agent(tenant, tools=(get_slots, book, get_services))

    # Bước 4: lấy thread cho session này
    thread_id = get_or_create_thread(req.session_id)

    # Bước 5: gửi message và nhận reply
    reply = await send_message(
        agent_id=agent_id,
        thread_id=thread_id,
        user_message=req.message,
        tools_context={"tenant_id": str(tenant.id)},
    )

    return ChatResponse(reply=reply, session_id=req.session_id)


@router.get("/{slug}")
async def chat_page(slug: str):
    return FileResponse("static/chat.html")