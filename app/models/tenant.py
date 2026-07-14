import uuid
from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class Tenant(Base, TimestampMixin):
    # __tablename__ báo SQLAlchemy tên bảng trong PostgreSQL là gì
    # nếu không có dòng này sẽ bị lỗi
    __tablename__ = "tenants"

    # UUID thay vì int tự tăng — lý do:
    # int tự tăng bị đoán được (user thấy id=1, id=2 → biết có bao nhiêu tenant)
    # UUID random hoàn toàn, không đoán được
    # as_uuid=True: Python nhận UUID object thay vì string thô
    # default=uuid.uuid4: Python tự tạo UUID mới mỗi khi INSERT
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # unique=True: không cho phép 2 tenant có cùng slug
    # index=True: tạo index → query WHERE slug = '...' sẽ nhanh hơn
    # nullable=False: bắt buộc phải có giá trị, không được để trống
    slug = Column(String(100), unique=True, nullable=False, index=True)

    name = Column(String(200), nullable=False)

    # Tên con AI khi chat với khách — ví dụ "Mai", "Linh", "Bot"
    persona_name = Column(String(100), nullable=False, default="Assistant")

    # Text thay vì String vì nội dung dài không giới hạn
    # String(200) giới hạn 200 ký tự, Text thì không giới hạn
    persona_prompt = Column(Text, nullable=False)

    timezone = Column(String(50), nullable=False, default="Asia/Ho_Chi_Minh")

    # Dùng để bật/tắt tenant mà không cần xóa data
    # xóa thì mất hết lịch sử booking — không muốn vậy
    is_active = Column(Boolean, default=True, nullable=False)

    # created_at và updated_at tự động có từ TimestampMixin
    # không cần viết lại ở đây

    # Relationship — truy cập services và bookings từ tenant object
    # cascade="all, delete-orphan": xóa tenant → tự xóa services/bookings
    services = relationship("Service", back_populates="tenant", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="tenant")
    operating_hours = relationship(
    "OperatingHours",
    back_populates="tenant",
    cascade="all, delete-orphan"
)