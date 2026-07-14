"""
Seed script — tạo SalonBot tenant và services mẫu.

Chạy: python -m scripts.seed
Điều kiện: database đang chạy và đã migrate (alembic upgrade head)
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

# Import settings để lấy DATABASE_URL từ .env
from app.core.config import get_settings

# Import models để tạo object
from app.models.tenant import Tenant
from app.models.service import Service
from app.models import booking  # noqa: F401 - registers Booking for relationship() lookups

settings = get_settings()


# Data mẫu cho SalonBot
# Đây là persona prompt — agent sẽ đọc cái này để biết mình là ai
SALON_MAI_PROMPT = """
Bạn là Mai, trợ lý đặt lịch thân thiện của Salon Mai.
Nhiệm vụ của bạn:
- Giới thiệu dịch vụ và báo giá khi khách hỏi
- Kiểm tra slot trống và đặt lịch cho khách
- Luôn xác nhận tên và số điện thoại trước khi đặt lịch
- Trả lời ngắn gọn, thân thiện, dùng tiếng Việt

Lưu ý: Không bịa thông tin. Nếu không biết thì nói không biết.
"""

# Danh sách dịch vụ — price đơn vị VND
SERVICES = [
    {
        "name": "Cắt tóc + gội đầu",
        "description": "Cắt theo yêu cầu, gội đầu và sấy khô",
        "duration_min": 60,
        "price": 150000,
    },
    {
        "name": "Nhuộm tóc",
        "description": "Nhuộm màu toàn bộ với thuốc nhuộm cao cấp",
        "duration_min": 120,
        "price": 350000,
    },
    {
        "name": "Uốn tóc",
        "description": "Uốn xoăn hoặc uốn duỗi theo yêu cầu",
        "duration_min": 150,
        "price": 400000,
    },
    {
        "name": "Ủ tóc phục hồi",
        "description": "Ủ dưỡng chất phục hồi tóc hư tổn",
        "duration_min": 45,
        "price": 120000,
    },
    {
        "name": "Gội đầu + massage",
        "description": "Gội đầu kết hợp massage thư giãn",
        "duration_min": 30,
        "price": 80000,
    },
]


async def seed():
    # Tạo engine kết nối DB — giống session.py nhưng dùng riêng cho script này
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        # Kiểm tra tenant đã tồn tại chưa — không tạo trùng
        result = await db.execute(
            select(Tenant).where(Tenant.slug == "salon-mai")
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Nếu đã có thì báo và dừng — không ghi đè
            print("Tenant 'salon-mai' đã tồn tại — bỏ qua seed.")
            return

        # Tạo tenant mới
        tenant = Tenant(
            slug="salon-mai",
            name="Salon Mai",
            persona_name="Mai",
            persona_prompt=SALON_MAI_PROMPT,
            timezone="Asia/Ho_Chi_Minh",
            is_active=True,
        )
        db.add(tenant)

        # flush() — ghi tenant vào DB trong transaction hiện tại
        # chưa commit nhưng tenant.id đã có giá trị
        # cần tenant.id để tạo services bên dưới
        await db.flush()

        # Tạo services — gắn vào tenant vừa tạo
        for svc_data in SERVICES:
            service = Service(
                tenant_id=tenant.id,  # lấy id vừa được flush
                currency="VND",
                **svc_data  # unpack dict thành keyword arguments
            )
            db.add(service)

        # commit() — ghi tất cả vào DB trong 1 transaction
        # nếu có lỗi ở bất kỳ bước nào thì rollback toàn bộ
        await db.commit()

        print(f"Đã tạo tenant: {tenant.name} (slug: {tenant.slug})")
        print(f"Đã tạo {len(SERVICES)} services:")
        for svc in SERVICES:
            print(f"  - {svc['name']}: {svc['price']:,} VND / {svc['duration_min']} phút")

    await engine.dispose()  # đóng kết nối sau khi xong


if __name__ == "__main__":
    asyncio.run(seed())