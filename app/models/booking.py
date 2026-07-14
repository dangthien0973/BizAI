import uuid
import enum
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


# Python enum — giới hạn status chỉ được là 1 trong 4 giá trị này
# pending: vừa đặt, chờ xác nhận
# confirmed: chủ tiệm đã xác nhận
# cancelled: đã hủy
# completed: đã hoàn thành
class BookingStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 2 foreign key — booking thuộc về 1 tenant VÀ 1 service
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    service_id = Column(
        UUID(as_uuid=True),
        ForeignKey("services.id"),
        nullable=False
    )

    # Thông tin khách — agent thu thập qua chat
    customer_name = Column(String(200), nullable=False)
    customer_phone = Column(String(20), nullable=False)

    # timezone=True: lưu kèm múi giờ (+07:00)
    # quan trọng: server có thể chạy ở UTC nhưng khách ở Việt Nam
    # nếu không lưu timezone → sai giờ 7 tiếng
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    # end_time = start_time + service.duration_min — tính khi tạo booking

    # Enum: SQLAlchemy tự validate, không cho ghi giá trị ngoài danh sách
    status = Column(
        Enum(BookingStatus),
        nullable=False,
        default=BookingStatus.pending
    )

    notes = Column(Text, nullable=True)  # ghi chú thêm của khách

    # Relationships
    tenant = relationship("Tenant", back_populates="bookings")
    service = relationship("Service", back_populates="bookings")