from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.v1 import router as api_router

app = FastAPI(
    title="BizAgent API",
    description="AI booking agent platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Page routes (trước API router) ───────────────────────
# Quan trọng: các route trả về HTML phải đặt TRƯỚC include_router
# vì FastAPI match theo thứ tự — nếu API router đặt trước,
# nó sẽ match /chat/{slug} như là API endpoint thay vì trang HTML

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/onboarding")
async def onboarding_page():
    return FileResponse("static/onboarding.html")

@app.get("/chat/{slug}")
async def chat_page(slug: str):
    return FileResponse("static/chat.html")

@app.get("/admin/{slug}")
async def admin_page(slug: str):
    return FileResponse("static/admin.html")

# ── API router (sau page routes) ─────────────────────────
app.include_router(api_router, prefix="/api/v1")