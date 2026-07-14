import uuid
from sqlalchemy import Column, String, Integer, Numeric, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class Service(Base, TimestampMixin):
    __tablename__ = "services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ForeignKey — ràng buộc tenant_id phải tồn tại trong bảng tenants
    # ondelete="CASCADE": nếu tenant bị xóa → services của nó tự xóa theo
    # không có CASCADE: xóa tenant sẽ bị lỗi vì còn services đang tham chiếu
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True   # hay query WHERE tenant_id = '...' nên cần index
    )

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)  # mô tả không bắt buộc

    # Thời gian thực hiện dịch vụ — dùng để tính slot trống
    # ví dụ: cắt tóc 60 phút, nhuộm 120 phút
    duration_min = Column(Integer, nullable=False, default=60)

    # Numeric(10, 2): tối đa 10 chữ số, 2 số sau dấu phẩy
    # 99999999.99 là giá tối đa — đủ dùng cho VND
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="VND")

    is_active = Column(Boolean, default=True, nullable=False)

    # Relationship — cho phép Python đọc tenant từ service object
    # ví dụ: service.tenant.name mà không cần query thêm
    # back_populates="services": bên Tenant cũng có relationship ngược lại
    tenant = relationship("Tenant", back_populates="services")
    bookings = relationship("Booking", back_populates="service")