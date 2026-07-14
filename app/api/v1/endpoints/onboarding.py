from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import time
import re

from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.service import Service
from app.models.operating_hours import OperatingHours
from app.schemas.onboarding import OnboardingRequest, OnboardingResponse

router = APIRouter()


def generate_slug(shop_name: str) -> str:
    """
    Sinh slug từ tên tiệm.
    "Nail Lan"     → "nail-lan"
    "Salon Mai ơi" → "salon-mai-oi"
    """
    # Bảng chuyển ký tự tiếng Việt → không dấu
    vn_map = {
        'à':'a','á':'a','ả':'a','ã':'a','ạ':'a',
        'ă':'a','ắ':'a','ặ':'a','ằ':'a','ẳ':'a','ẵ':'a',
        'â':'a','ấ':'a','ầ':'a','ẩ':'a','ẫ':'a','ậ':'a',
        'è':'e','é':'e','ẻ':'e','ẽ':'e','ẹ':'e',
        'ê':'e','ế':'e','ề':'e','ể':'e','ễ':'e','ệ':'e',
        'ì':'i','í':'i','ỉ':'i','ĩ':'i','ị':'i',
        'ò':'o','ó':'o','ỏ':'o','õ':'o','ọ':'o',
        'ô':'o','ố':'o','ồ':'o','ổ':'o','ỗ':'o','ộ':'o',
        'ơ':'o','ớ':'o','ờ':'o','ở':'o','ỡ':'o','ợ':'o',
        'ù':'u','ú':'u','ủ':'u','ũ':'u','ụ':'u',
        'ư':'u','ứ':'u','ừ':'u','ử':'u','ữ':'u','ự':'u',
        'ỳ':'y','ý':'y','ỷ':'y','ỹ':'y','ỵ':'y',
        'đ':'d',
    }

    slug = shop_name.lower()

    # Thay ký tự tiếng Việt
    for vn, en in vn_map.items():
        slug = slug.replace(vn, en)

    # Thay khoảng trắng và ký tự đặc biệt bằng dấu gạch ngang
    slug = re.sub(r'[^a-z0-9]+', '-', slug)

    # Xóa dấu gạch ngang ở đầu và cuối
    slug = slug.strip('-')

    return slug


async def get_unique_slug(db: AsyncSession, base_slug: str) -> str:
    """
    Đảm bảo slug unique trong DB.
    Nếu "nail-lan" đã tồn tại thì thử "nail-lan-2", "nail-lan-3"...
    """
    slug = base_slug
    counter = 2

    while True:
        result = await db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        existing = result.scalar_one_or_none()

        if not existing:
            return slug  # slug này chưa có → dùng được

        # Đã tồn tại → thử thêm số
        slug = f"{base_slug}-{counter}"
        counter += 1


def build_persona_prompt(shop_name: str, persona_name: str) -> str:
    """
    Tự tạo persona prompt từ tên tiệm và tên AI.
    Chủ tiệm không cần biết khái niệm này.
    """
    return f"""
Bạn là {persona_name}, trợ lý đặt lịch thân thiện của {shop_name}.
Nhiệm vụ của bạn:
- Giới thiệu dịch vụ và báo giá khi khách hỏi
- Kiểm tra lịch trống và đặt lịch cho khách
- Luôn xác nhận tên và số điện thoại trước khi đặt lịch
- Xác nhận lại thông tin với khách trước khi book
- Trả lời ngắn gọn, thân thiện, dùng tiếng Việt
- Không bịa thông tin về dịch vụ hay giá
""".strip()


@router.post("/", response_model=OnboardingResponse, status_code=201)
async def onboarding(req: OnboardingRequest, db: AsyncSession = Depends(get_db)):
    # Bước 1: sinh slug từ tên tiệm
    base_slug = generate_slug(req.shop_name)
    slug = await get_unique_slug(db, base_slug)

    # Bước 2: tạo tenant
    tenant = Tenant(
        slug=slug,
        name=req.shop_name,
        persona_name=req.persona_name,
        persona_prompt=build_persona_prompt(req.shop_name, req.persona_name),
        timezone="Asia/Ho_Chi_Minh",
        is_active=True,
    )
    db.add(tenant)

    # flush để có tenant.id — cần cho services và operating_hours
    await db.flush()

    # Bước 3: tạo services
    for svc_data in req.services:
        service = Service(
            tenant_id=tenant.id,
            name=svc_data.name,
            description=svc_data.description,
            duration_min=svc_data.duration_min,
            price=svc_data.price,
            currency="VND",
            is_active=True,
        )
        db.add(service)

    # Bước 4: tạo operating_hours
    for oh_data in req.operating_hours:
        # Parse "08:00" → time(8, 0)
        def parse_time(t: str | None):
            if t is None:
                return None
            h, m = map(int, t.split(":"))
            return time(h, m)

        oh = OperatingHours(
            tenant_id=tenant.id,
            day_of_week=oh_data.day_of_week,
            open_time=parse_time(oh_data.open_time),
            close_time=parse_time(oh_data.close_time),
            is_closed=oh_data.is_closed,
        )
        db.add(oh)

    # Bước 5: commit tất cả trong 1 transaction
    # nếu lỗi bất kỳ bước nào → rollback hết
    await db.commit()

    return OnboardingResponse(
        tenant_slug=slug,
        chat_url=f"/chat/{slug}",
        message=f"Tạo thành công! Trợ lý AI của {req.shop_name} đã sẵn sàng.",
    )