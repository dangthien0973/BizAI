import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select

from app.db.session import SyncSessionLocal
from app.models.service import Service
from app.models.booking import Booking, BookingStatus

# Giờ làm việc mặc định — chưa có cột business_hours trên Tenant nên tạm hardcode
BUSINESS_HOURS_START = 9   # 09:00
BUSINESS_HOURS_END = 18    # 18:00
SLOT_STEP_MIN = 30

# Booking.start_time/end_time lưu timezone=True (offset-aware) — phải gắn
# tzinfo khi tạo datetime ở đây, nếu không so sánh sẽ lỗi
# "can't compare offset-naive and offset-aware datetimes"
TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def make_booking_tools(tenant_id: str):
    """
    Tạo cặp hàm get_available_slots / book_appointment với tenant_id
    đã "đóng gói" sẵn (closure). Dùng session đồng bộ riêng — Azure
    AgentsClient gọi tool function bằng function(**args) đồng bộ,
    không await coroutine, nên không thể dùng AsyncSession ở đây.
    """

    def get_available_slots(service_id: str, date: str) -> str:
        """
        Lấy danh sách khung giờ trống trong ngày cho 1 dịch vụ.

        Args:
            service_id: ID dịch vụ khách muốn đặt (lấy từ get_services())
            date: Ngày muốn đặt, định dạng YYYY-MM-DD

        Returns:
            Danh sách khung giờ trống dưới dạng JSON
        """
        with SyncSessionLocal() as db:
            result = db.execute(
                select(Service).where(Service.id == service_id, Service.tenant_id == tenant_id)
            )
            service = result.scalar_one_or_none()
            if not service:
                return json.dumps({"error": "Không tìm thấy dịch vụ"}, ensure_ascii=False)

            try:
                day = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                return json.dumps({"error": "Ngày không hợp lệ, dùng định dạng YYYY-MM-DD"}, ensure_ascii=False)

            day_start = datetime.combine(day, datetime.min.time()).replace(hour=BUSINESS_HOURS_START, tzinfo=TZ)
            day_end = datetime.combine(day, datetime.min.time()).replace(hour=BUSINESS_HOURS_END, tzinfo=TZ)

            # Lấy các booking đã có trong ngày để loại trừ khung giờ trùng
            result = db.execute(
                select(Booking).where(
                    Booking.tenant_id == tenant_id,
                    Booking.start_time < day_end,
                    Booking.end_time > day_start,
                    Booking.status != BookingStatus.cancelled,
                )
            )
            existing = result.scalars().all()

            duration = timedelta(minutes=service.duration_min)
            step = timedelta(minutes=SLOT_STEP_MIN)

            slots = []
            cursor = day_start
            while cursor + duration <= day_end:
                slot_end = cursor + duration
                overlap = any(cursor < b.end_time and slot_end > b.start_time for b in existing)
                if not overlap:
                    slots.append(cursor.strftime("%H:%M"))
                cursor += step

            return json.dumps(
                {"date": date, "service_id": service_id, "available_slots": slots},
                ensure_ascii=False,
            )

    def book_appointment(
        service_id: str,
        customer_name: str,
        customer_phone: str,
        date: str,
        time: str,
    ) -> str:
        """
        Tạo lịch đặt mới cho khách hàng.

        Args:
            service_id: ID dịch vụ khách muốn đặt (lấy từ get_services())
            customer_name: Tên khách hàng
            customer_phone: Số điện thoại khách hàng
            date: Ngày đặt lịch, định dạng YYYY-MM-DD
            time: Giờ đặt lịch, định dạng HH:MM

        Returns:
            Kết quả đặt lịch (thành công hoặc lỗi) dưới dạng JSON
        """
        with SyncSessionLocal() as db:
            result = db.execute(
                select(Service).where(Service.id == service_id, Service.tenant_id == tenant_id)
            )
            service = result.scalar_one_or_none()
            if not service:
                return json.dumps({"error": "Không tìm thấy dịch vụ"}, ensure_ascii=False)

            try:
                start_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
            except ValueError:
                return json.dumps({"error": "Ngày hoặc giờ không hợp lệ"}, ensure_ascii=False)

            end_time = start_time + timedelta(minutes=service.duration_min)

            # Kiểm tra trùng lịch trước khi tạo booking mới
            result = db.execute(
                select(Booking).where(
                    Booking.tenant_id == tenant_id,
                    Booking.status != BookingStatus.cancelled,
                    Booking.start_time < end_time,
                    Booking.end_time > start_time,
                )
            )
            if result.scalars().first():
                return json.dumps(
                    {"error": "Khung giờ này đã có người đặt, vui lòng chọn giờ khác"},
                    ensure_ascii=False,
                )

            booking = Booking(
                tenant_id=tenant_id,
                service_id=service_id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                start_time=start_time,
                end_time=end_time,
                status=BookingStatus.pending,
            )
            db.add(booking)
            db.commit()
            db.refresh(booking)

            return json.dumps(
                {
                    "success": True,
                    "booking_id": str(booking.id),
                    "service": service.name,
                    "date": date,
                    "time": time,
                    "customer_name": customer_name,
                },
                ensure_ascii=False,
            )

    return get_available_slots, book_appointment
