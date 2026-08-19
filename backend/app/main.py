import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.router import api_router
from app.api.endpoints.mvp import router as mvp_router

# Configure base logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up WA Mark 2 Backend")
    from app.db.session import SessionLocal
    from app.db.init_db import init_db
    db = SessionLocal()
    try:
        init_db(db)
    except Exception as e:
        logger.error(f"DB init failed (non-fatal): {e}")
    finally:
        db.close()
    yield
    # Shutdown
    logger.info("Shutting down WA Mark 2 Backend")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # update in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(mvp_router, prefix="/api", tags=["mvp"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
