import logging
import json
import os
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime
import requests
import bcrypt

from app.automation.scheduler import Scheduler
from app.database.connection import init_db
from app.database.repository import Repository, get_repository
from app.database.models import Account as DBAccount, Campaign as DBCampaign
from app.config import settings

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
        raise HTTPException(status_code=403, detail="Could not validate API KEY")
    return api_key_header

scheduler = Scheduler()

@app.on_event("startup")
async def startup_event():
    logger.info("Starting API...")
    try:
        init_db()
        await scheduler.start()
    except Exception as e:
        import traceback
        logger.error(f"STARTUP FAILED: {e}")
        logger.error(traceback.format_exc())
        raise

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down API...")
    await scheduler.stop()

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
    password: Optional[str] = None
    session_data: Optional[str] = None

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
    ai_instructions: Optional[str] = None
    schedule: ScheduleSchema
    daily_limit: Optional[int] = 50

class CampaignResponse(BaseModel):
    id: str
    name: str
    platform: Optional[str] = None
    campaign_type: str
    status: str
    daily_limit: int

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    username: str
    token: str

class OpenClawExecuteRequest(BaseModel):
    action: str
    targets: List[str]
    message: Optional[str] = None
    count: Optional[int] = 50
    credentials: Optional[Dict[str, str]] = None

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
    return [AccountResponse(id=a.id, platform=a.platform, username=a.username, is_active=a.is_active) for a in accounts]

@app.post("/api/accounts", response_model=AccountResponse)
def create_account(account: AccountCreate, repo: Repository = Depends(get_repository), api_key: str = Depends(get_api_key)):
    new_account = DBAccount(
        id=str(uuid4()), platform=account.platform.value, username=account.username,
        password=account.password, display_name=account.username, session_data=account.session_data,
        is_active=True, created_at=int(datetime.now().timestamp())
    )
    repo.create_account(new_account)
    return AccountResponse(id=new_account.id, platform=new_account.platform, username=new_account.username, is_active=new_account.is_active)

@app.post("/api/campaigns", response_model=CampaignResponse)
def create_campaign(campaign: CampaignCreate, repo: Repository = Depends(get_repository), api_key: str = Depends(get_api_key)):
    new_campaign = DBCampaign(
        id=str(uuid4()), account_id=campaign.account_id, name=campaign.name,
        campaign_type=campaign.campaign_type.value, status="draft",
        targeting_json=json.dumps(campaign.targeting.model_dump()),
        message_template=campaign.message_template, ai_instructions=campaign.ai_instructions,
        schedule_json=json.dumps(campaign.schedule.model_dump()),
        daily_limit=campaign.daily_limit or 50, created_at=int(datetime.now().timestamp())
    )
    repo.create_campaign(new_campaign)
    return CampaignResponse(id=new_campaign.id, name=new_campaign.name, platform=None, campaign_type=new_campaign.campaign_type, status=new_campaign.status, daily_limit=new_campaign.daily_limit)

@app.get("/api/campaigns", response_model=List[CampaignResponse])
def list_campaigns(repo: Repository = Depends(get_repository), api_key: str = Depends(get_api_key)):
    campaigns = repo.list_campaigns()
    return [CampaignResponse(id=c.id, name=c.name, campaign_type=c.campaign_type, status=c.status, daily_limit=c.daily_limit) for c in campaigns]

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

@app.post("/api/optimize")
def optimize_campaign(campaign_id: str, api_key: str = Depends(get_api_key)):
    try:
        response = requests.post(f"{settings.RUST_SERVICE_URL}/optimize", json={"campaign_id": campaign_id}, timeout=settings.RUST_SERVICE_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to call Rust service: {e}")
        raise HTTPException(status_code=503, detail="Optimization service unavailable")

@app.post("/api/login", response_model=LoginResponse)
def login(request: LoginRequest, repo: Repository = Depends(get_repository)):
    user = repo.get_user(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    stored_hash = user['hashed_password']
    if not bcrypt.checkpw(request.password.encode('utf-8'), stored_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return LoginResponse(username=request.username, token="mock-session-token")

@app.get("/api/settings")
def get_all_settings(repo: Repository = Depends(get_repository), api_key: str = Depends(get_api_key)):
    return repo.get_all_settings()

@app.post("/api/settings")
def update_setting(data: Dict[str, Any], repo: Repository = Depends(get_repository), api_key: str = Depends(get_api_key)):
    for key, value in data.items():
        repo.update_setting(key, str(value))
    if "USE_ANDROID_EMULATOR" in data:
        settings.USE_ANDROID_EMULATOR = str(data["USE_ANDROID_EMULATOR"]).lower() in ["true", "1", "yes"]
    return {"status": "success"}

@app.post("/api/register", response_model=LoginResponse)
def register(request: LoginRequest, repo: Repository = Depends(get_repository)):
    if repo.get_user(request.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    repo.create_user(request.username, hashed)
    return LoginResponse(username=request.username, token="mock-session-token")

@app.post("/api/openclaw/execute", tags=["openclaw"])
async def execute_openclaw(request: OpenClawExecuteRequest, api_key: str = Depends(get_api_key)):
    """
    Trigger an OpenClaw IG automation action via the gateway RPC.
    OpenClaw gateway must be running on the same VPS.
    """
    openclaw_url = os.getenv("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")

    tool_map = {"follow": "ig_follow", "dm": "ig_send_dm", "unfollow": "ig_unfollow", "scrape": "ig_scrape_followers", "bombing": "ig_bombing_campaign"}
    tool_name = tool_map.get(request.action)
    if not tool_name:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}. Valid: {list(tool_map.keys())}")

    payload = {"tool": tool_name, "params": {}}

    if request.action == "bombing":
        payload["params"] = {"targets": request.targets, "action": "follow", "message": request.message or "", "count": request.count or 50}
    elif request.action == "scrape":
        payload["params"] = {"username": request.targets[0] if request.targets else "", "count": request.count or 100}
    elif request.action == "dm":
        payload["params"] = {"username": request.targets[0] if request.targets else "", "message": request.message or ""}
    else:
        payload["params"] = {"username": request.targets[0] if request.targets else ""}

    try:
        resp = requests.post(f"{openclaw_url}/rpc/execute", json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"OpenClaw execution failed: {e}")
        raise HTTPException(status_code=502, detail=f"OpenClaw gateway error: {e}")

@app.post("/api/openclaw/webhook", tags=["openclaw"])
async def openclaw_webhook(data: Dict[str, Any], api_key: str = Depends(get_api_key)):
    command = data.get("command", "")
    params = data.get("params", {})
    logger.info(f"OpenClaw webhook: command={command}")
    return {"status": "received", "command": command}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
