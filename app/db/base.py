from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import DeclarativeBase


# Base là class gốc — mọi model đều kế thừa từ đây
# SQLAlchemy dùng Base.metadata để biết có những bảng nào
class Base(DeclarativeBase):
    pass


# Mixin — giống interface trong C#, nhưng có sẵn implementation
# Bất kỳ model nào kế thừa TimestampMixin sẽ tự có 2 cột này
class TimestampMixin:
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),  # DB tự điền khi INSERT
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()         # DB tự cập nhật khi UPDATE
    )