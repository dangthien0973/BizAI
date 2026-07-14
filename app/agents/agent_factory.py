from azure.ai.agents import AgentsClient
from azure.ai.agents.models import FunctionTool, ToolSet
from azure.identity import DefaultAzureCredential

from app.core.config import get_settings
from app.models.tenant import Tenant

settings = get_settings()

_agent_cache: dict[str, str] = {}
_client: AgentsClient | None = None


def get_ai_client() -> AgentsClient:
    global _client
    if _client is None:
        _client = AgentsClient(
            endpoint=settings.azure_ai_project_endpoint,
            credential=DefaultAzureCredential(),
        )
    return _client


async def get_or_create_agent(tenant: Tenant, tools: tuple) -> str:
    """
    Tạo agent cho tenant với tools được truyền vào từ bên ngoài.
    tools: tuple của các hàm từ make_booking_tools() và get_services
    """
    client = get_ai_client()

    # tools được truyền vào — không import trực tiếp ở đây
    # vì cả booking tools và catalog tools đều cần db session,
    # tạo từ chat endpoint (closure với tenant_id đóng gói sẵn)
    # Phải đăng ký lại mỗi request dù agent đã cache — closures này
    # gắn với db session của request hiện tại, session cũ đã đóng
    functions = FunctionTool(functions=set(tools))

    toolset = ToolSet()
    toolset.add(functions)

    # Đăng ký toolset để SDK tự động gọi các hàm Python này
    # khi agent yêu cầu tool call trong lúc chạy run (create_and_process)
    client.enable_auto_function_calls(toolset)

    if tenant.slug in _agent_cache:
        return _agent_cache[tenant.slug]

    system_prompt = f"""
Bạn là {tenant.persona_name}, trợ lý đặt lịch của {tenant.name}.

{tenant.persona_prompt}

Quy tắc bắt buộc:
- Khi khách hỏi dịch vụ hoặc giá: gọi get_services() trước
- Khi khách muốn xem lịch trống: gọi get_available_slots()
- Khi khách xác nhận đặt lịch: gọi book_appointment()
- Luôn hỏi tên và số điện thoại trước khi book
- Xác nhận lại thông tin với khách trước khi gọi book_appointment()
- Không bịa thông tin về dịch vụ hay giá
"""

    agent = client.create_agent(
        model=settings.azure_ai_model,
        name=f"bizagent-{tenant.slug}",
        instructions=system_prompt,
        toolset=toolset,
    )

    _agent_cache[tenant.slug] = agent.id
    print(f"Created agent for tenant '{tenant.slug}': {agent.id}")
    return agent.id
