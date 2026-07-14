from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re


class ServiceInput(BaseModel):
    """Một dịch vụ trong form onboarding"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    duration_min: int = Field(..., ge=15, le=480)
    # ge=15: tối thiểu 15 phút, le=480: tối đa 8 tiếng
    price: float = Field(..., ge=0)
    # ge=0: giá không được âm


class OperatingHoursInput(BaseModel):
    """Giờ mở cửa 1 ngày trong tuần"""
    day_of_week: int = Field(..., ge=0, le=6)
    # ge=0=Thứ 2, le=6=Chủ nhật

    open_time: Optional[str] = None
    # format "HH:MM" — nullable vì ngày nghỉ không cần

    close_time: Optional[str] = None

    is_closed: bool = False

    @field_validator("open_time", "close_time")
    @classmethod
    def validate_time_format(cls, v):
        """Kiểm tra format HH:MM — ví dụ 08:00, 17:30"""
        if v is None:
            return v
        # regex check HH:MM
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("Thời gian phải có định dạng HH:MM, ví dụ: 08:00")
        hour, minute = map(int, v.split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Giờ phải từ 00-23, phút phải từ 00-59")
        return v


class OnboardingRequest(BaseModel):
    """Toàn bộ data từ form onboarding — 1 request tạo hết mọi thứ"""
    shop_name: str = Field(..., min_length=2, max_length=200)
    persona_name: str = Field(..., min_length=1, max_length=100)
    # persona_prompt mặc định — chủ tiệm không cần biết đến khái niệm này
    # backend tự tạo từ shop_name và persona_name

    services: list[ServiceInput] = Field(..., min_length=1)
    # min_length=1: phải có ít nhất 1 dịch vụ

    operating_hours: list[OperatingHoursInput] = Field(..., min_length=7, max_length=7)
    # Đúng 7 ngày — form luôn gửi đủ 7 ngày, ngày nghỉ thì is_closed=True

    @field_validator("operating_hours")
    @classmethod
    def validate_all_days_present(cls, v):
        """Đảm bảo có đủ 7 ngày từ 0 đến 6"""
        days = sorted([h.day_of_week for h in v])
        if days != list(range(7)):
            raise ValueError("Phải có đủ 7 ngày trong tuần (0=Thứ 2 đến 6=Chủ nhật)")
        return v

    @field_validator("operating_hours")
    @classmethod
    def validate_open_close_if_not_closed(cls, v):
        """Nếu ngày không nghỉ thì phải có giờ mở và đóng"""
        for h in v:
            if not h.is_closed:
                if not h.open_time or not h.close_time:
                    raise ValueError(
                        f"Ngày {h.day_of_week} không nghỉ nhưng thiếu giờ mở hoặc đóng cửa"
                    )
        return v


class OnboardingResponse(BaseModel):
    """Response trả về sau khi tạo tenant thành công"""
    tenant_slug: str
    chat_url: str
    message: str
