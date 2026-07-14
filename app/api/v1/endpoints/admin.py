from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from datetime import datetime, date
from zoneinfo import ZoneInfo
import uuid

from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.booking import Booking, BookingStatus
from app.models.service import Service

router = APIRouter()

TZ = ZoneInfo("Asia/Ho_Chi_Minh")


# ── Schemas ───────────────────────────────────────────────

class ServiceInfo(BaseModel):
    name: str
    duration_min: int

    class Config:
        from_attributes = True


class BookingOut(BaseModel):
    id: uuid.UUID
    customer_name: str
    customer_phone: str
    start_time: datetime
    end_time: datetime
    status: str
    notes: str | None
    service: ServiceInfo

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: BookingStatus


# ── Endpoints ─────────────────────────────────────────────

@router.get("/{slug}/bookings", response_model=list[BookingOut])
async def list_bookings(
    slug: str,
    target_date: str | None = None,  # query param: ?target_date=2025-07-15
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy danh sách booking của tiệm theo ngày.
    Mặc định là hôm nay nếu không truyền target_date.
    """
    # Load tenant
    result = await db.execute(
        select(Tenant).where(Tenant.slug == slug, Tenant.is_active == True)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Parse ngày — mặc định hôm nay
    if target_date:
        query_date = date.fromisoformat(target_date)
    else:
        query_date = datetime.now(TZ).date()

    # Tạo khoảng thời gian đầu ngày và cuối ngày theo timezone VN
    start_of_day = datetime(
        query_date.year, query_date.month, query_date.day,
        0, 0, 0, tzinfo=TZ
    )
    end_of_day = datetime(
        query_date.year, query_date.month, query_date.day,
        23, 59, 59, tzinfo=TZ
    )

    # Query bookings + load service luôn trong 1 query (tránh N+1)
    # selectinload: SQLAlchemy tự JOIN và map service vào booking object
    result = await db.execute(
        select(Booking)
        .where(
            and_(
                Booking.tenant_id == tenant.id,
                Booking.start_time >= start_of_day,
                Booking.start_time <= end_of_day,
            )
        )
        .options(selectinload(Booking.service))
        .order_by(Booking.start_time)
    )
    bookings = result.scalars().all()
    return bookings


@router.patch("/{slug}/bookings/{booking_id}", response_model=BookingOut)
async def update_booking_status(
    slug: str,
    booking_id: uuid.UUID,
    body: StatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Cập nhật status booking — confirm hoặc cancel.
    Chỉ cho phép update booking thuộc đúng tenant này.
    """
    # Load tenant
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.slug == slug)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Load booking — đảm bảo booking thuộc tenant này
    booking_result = await db.execute(
        select(Booking)
        .where(
            and_(
                Booking.id == booking_id,
                Booking.tenant_id == tenant.id,  # security check
            )
        )
        .options(selectinload(Booking.service))
    )
    booking = booking_result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Không cho update booking đã completed
    if booking.status == BookingStatus.completed:
        raise HTTPException(
            status_code=400,
            detail="Không thể thay đổi booking đã hoàn thành"
        )

    booking.status = body.status
    await db.commit()
    await db.refresh(booking)
    return booking