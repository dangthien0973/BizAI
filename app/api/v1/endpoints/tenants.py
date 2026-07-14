from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid

from app.db.session import get_db
from app.models.tenant import Tenant

router = APIRouter()


# Pydantic schema — định nghĩa JSON trả về cho client
# Khác với SQLAlchemy model (mô tả bảng DB)
# Pydantic schema mô tả shape của JSON request/response
class TenantOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    persona_name: str
    is_active: bool

    class Config:
        # Cho phép đọc từ SQLAlchemy object trực tiếp
        # thay vì phải convert tay từng field
        from_attributes = True


class TenantCreate(BaseModel):
    slug: str
    name: str
    persona_name: str
    persona_prompt: str


# GET /api/v1/tenants
# Depends(get_db) — FastAPI tự động:
#   1. Gọi get_db() để mở session
#   2. Truyền session vào hàm này qua tham số db
#   3. Đóng session sau khi hàm xong
# Đây là Dependency Injection — giống constructor injection trong .NET
@router.get("/", response_model=list[TenantOut])
async def list_tenants(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Tenant).where(Tenant.is_active == True)
    )
    # scalars() — lấy danh sách Tenant object thay vì Row object
    # all() — lấy tất cả kết quả thành list
    tenants = result.scalars().all()
    return tenants


# GET /api/v1/tenants/salon-mai
@router.get("/{slug}", response_model=TenantOut)
async def get_tenant(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Tenant).where(Tenant.slug == slug)
    )
    # scalar_one_or_none() — lấy đúng 1 kết quả hoặc None
    # nếu có 2 kết quả trở lên thì raise lỗi (không xảy ra vì slug unique)
    tenant = result.scalar_one_or_none()

    if not tenant:
        # FastAPI tự convert thành HTTP 404 response
        raise HTTPException(status_code=404, detail="Tenant not found")

    return tenant


# POST /api/v1/tenants
@router.post("/", response_model=TenantOut, status_code=201)
async def create_tenant(data: TenantCreate, db: AsyncSession = Depends(get_db)):
    tenant = Tenant(
        slug=data.slug,
        name=data.name,
        persona_name=data.persona_name,
        persona_prompt=data.persona_prompt,
    )

    db.add(tenant)         # thêm vào session — chưa INSERT vào DB
    await db.commit()      # INSERT thật vào DB
    await db.refresh(tenant)  # đọc lại từ DB — lấy id, created_at vừa được tạo

    return tenant