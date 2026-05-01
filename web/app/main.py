import logging
import json
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime
import requests

from app.automation.scheduler import Scheduler
from app.database.connection import init_db
from app.database.repository import Repository, get_repository
from app.database.models import Account as DBAccount, Campaign as DBCampaign
from app.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API")

app = FastAPI(title="SocialGrowthAI API")

cors_allowed_origins = [origin.strip() for origin in settings.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if not api_key_header or api_key_header != settings.API_KEY:
        raise HTTPException(
            status_code=403, detail="Could not validate API KEY"
        )
    return api_key_header

scheduler = Scheduler()

@app.on_event("startup")
async def startup_event():
    logger.info("Starting API...")
    init_db()
    await scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down API...")
    await scheduler.stop()

# --- Pydantic Models ---
from enum import Enum

class PlatformType(str, Enum):
    instagram = "instagram"
    twitter = "twitter"
    facebook = "facebook"
    linkedin = "linkedin"

class CampaignType(str, Enum):
    growth = "growth"
    outreach = "outreach"

class AccountCreate(BaseModel):
    platform: PlatformType
    username: str
    session_data: Optional[str] = None # JSON string of cookies

class AccountResponse(BaseModel):
    id: str
    platform: PlatformType
    username: str
    is_active: bool

class TargetingSchema(BaseModel):
    tags: List[str]
    keywords: Optional[List[str]] = []

class ScheduleSchema(BaseModel):
    days: List[str]
    start_time: str
    end_time: str
    timezone: str

class CampaignCreate(BaseModel):
    account_id: str
    name: str
    campaign_type: CampaignType
    targeting: TargetingSchema
    message_template: str
    schedule: ScheduleSchema
    daily_limit: Optional[int] = 50

class CampaignResponse(BaseModel):
    id: str
    name: str
    status: str

# --- Endpoints ---

@app.get("/")
async def root():
    if settings.REDIRECT_ROOT_TO_FRONTEND and settings.FRONTEND_URL:
        return RedirectResponse(url=settings.FRONTEND_URL)
    return {"status": "running", "service": "SocialGrowthAI Backend"}

@app.get("/health/live")
async def health_live():
    return {"status": "ok"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/health/ready")
def health_ready(repo: Repository = Depends(get_repository)):
    try:
        repo.get_analytics_summary()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")
    return {"status": "ready"}

@app.get("/api/accounts", response_model=List[AccountResponse])
def list_accounts(repo: Repository = Depends(get_repository), api_key: str = Depends(get_api_key)):
    accounts = repo.list_accounts()
    return [
        AccountResponse(
            id=a.id,
            platform=a.platform,
            username=a.username,
            is_active=a.is_active
        ) for a in accounts
    ]

@app.post("/api/accounts", response_model=AccountResponse)
def create_account(account: AccountCreate, repo: Repository = Depends(get_repository), api_key: str = Depends(get_api_key)):
    new_account = DBAccount(
        id=str(uuid4()),
        platform=account.platform.value,
        username=account.username,
        display_name=account.username,
        session_data=account.session_data,
        is_active=True,
        created_at=int(datetime.now().timestamp())
    )
    repo.create_account(new_account)
    return AccountResponse(
        id=new_account.id,
        platform=new_account.platform,
        username=new_account.username,
        is_active=new_account.is_active
    )

@app.post("/api/campaigns", response_model=CampaignResponse)
def create_campaign(campaign: CampaignCreate, repo: Repository = Depends(get_repository), api_key: str = Depends(get_api_key)):
    new_campaign = DBCampaign(
        id=str(uuid4()),
        account_id=campaign.account_id,
        name=campaign.name,
        campaign_type=campaign.campaign_type.value,
        status="draft",
        targeting_json=json.dumps(campaign.targeting.model_dump()),
        message_template=campaign.message_template,
        schedule_json=json.dumps(campaign.schedule.model_dump()),
        daily_limit=campaign.daily_limit or 50,
        created_at=int(datetime.now().timestamp())
    )
    repo.create_campaign(new_campaign)
    return CampaignResponse(
        id=new_campaign.id,
        name=new_campaign.name,
        status=new_campaign.status
    )

@app.post("/api/campaigns/{campaign_id}/start")
async def start_campaign(campaign_id: str, api_key: str = Depends(get_api_key)):
    await scheduler.start_campaign(campaign_id)
    return {"status": "started", "campaign_id": campaign_id}

@app.post("/api/campaigns/{campaign_id}/stop")
async def stop_campaign(campaign_id: str, api_key: str = Depends(get_api_key)):
    await scheduler.stop_campaign(campaign_id)
    return {"status": "stopped", "campaign_id": campaign_id}

@app.get("/api/analytics/summary")
def get_analytics(repo: Repository = Depends(get_repository), api_key: str = Depends(get_api_key)):
    return repo.get_analytics_summary()

# Rust Integration Endpoint
@app.post("/api/optimize")
def optimize_campaign(campaign_id: str, api_key: str = Depends(get_api_key)):
    try:
        response = requests.post(
            f"{settings.RUST_SERVICE_URL}/optimize",
            json={"campaign_id": campaign_id},
            timeout=settings.RUST_SERVICE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to call Rust service: {e}")
        raise HTTPException(status_code=503, detail="Optimization service unavailable")
