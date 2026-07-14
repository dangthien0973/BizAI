import json

from sqlalchemy import select

from app.db.session import SyncSessionLocal
from app.models.service import Service


def make_catalog_tools(tenant_id: str):
    """
    Tạo hàm get_services với tenant_id đã "đóng gói" sẵn (closure).
    Dùng session đồng bộ riêng — Azure AgentsClient gọi tool function
    bằng function(**args) đồng bộ, không await coroutine.
    """

    def get_services() -> str:
        """
        Lấy danh sách dịch vụ và giá của tiệm.

        Returns:
            Danh sách dịch vụ với id, tên, giá, thời gian thực hiện dưới dạng JSON
        """
        with SyncSessionLocal() as db:
            result = db.execute(
                select(Service).where(Service.tenant_id == tenant_id, Service.is_active == True)
            )
            services = result.scalars().all()

            return json.dumps({
                "services": [
                    {
                        "id": str(s.id),
                        "name": s.name,
                        "price": float(s.price),
                        "duration_min": s.duration_min,
                    }
                    for s in services
                ],
                "currency": "VND",
            }, ensure_ascii=False)

    return get_services
