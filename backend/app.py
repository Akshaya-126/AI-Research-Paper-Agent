from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from backend.services.telegram_bot import (
    build_application,
    handle_update,
)


# ============================================================
# TELEGRAM APPLICATION
# ============================================================

telegram_app = build_application()


# ============================================================
# FASTAPI LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    # Initialize Telegram application.
    await telegram_app.initialize()

    # Start Telegram application.
    await telegram_app.start()

    print("Telegram application started.")

    yield

    # Stop Telegram application.
    await telegram_app.stop()

    # Shutdown Telegram application.
    await telegram_app.shutdown()

    print("Telegram application stopped.")


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="ResearchX AI",
    description="AI Research Paper Agent",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():

    return {
        "status": "online",
        "service": "ResearchX AI",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
    }


# ============================================================
# TELEGRAM WEBHOOK
# ============================================================

@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
):

    update_data = await request.json()

    await handle_update(
        telegram_app,
        update_data,
    )

    return {
        "ok": True,
    }