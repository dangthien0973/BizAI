import uuid
from sqlalchemy import Column, Integer, Boolean, Time, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class OperatingHours(Base):
    __tablename__ = "operating_hours"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 0=Thứ 2, 1=Thứ 3, 2=Thứ 4, 3=Thứ 5, 4=Thứ 6, 5=Thứ 7, 6=Chủ nhật
    day_of_week = Column(Integer, nullable=False)

    # Time — chỉ lưu giờ:phút, không có date
    # ví dụ: 08:00, 17:30
    # nullable vì ngày nghỉ không cần giờ mở/đóng
    open_time = Column(Time, nullable=True)
    close_time = Column(Time, nullable=True)

    # True = ngày này tiệm nghỉ
    # khi is_closed=True thì open_time/close_time bỏ qua
    is_closed = Column(Boolean, nullable=False, default=False)

    tenant = relationship("Tenant", back_populates="operating_hours")