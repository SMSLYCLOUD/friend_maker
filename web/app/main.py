import logging
import json
import asyncio
import os
import base64
from fastapi import FastAPI, HTTPException, Depends, Security, UploadFile, File
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime, timedelta
import requests
from urllib.parse import quote as url_quote
import bcrypt
import jwt as pyjwt

from app.automation.scheduler import Scheduler
from app.database.connection import init_db
from app.database.repository import Repository, get_repository
from app.database.models import Account as DBAccount, Campaign as DBCampaign
from app.config import settings
from app.telegram_bot import start_bot, stop_bot
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API")

app = FastAPI(title="SocialGrowthAI API")

cors_allowed_origins = [origin.strip() for origin in settings.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
security = HTTPBearer(auto_error=False)

JWT_SECRET = settings.API_KEY + "-jwt-secret-v1"
JWT_ALGO = "HS256"

def create_token(user_id: str, username: str) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    api_key: str = Depends(api_key_header),
    repo: Repository = Depends(get_repository)
):
    # Allow API key fallback for backward compat
    if api_key and api_key == settings.API_KEY:
        return {"id": "api-key-user", "username": "admin", "is_api_key": True}
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = pyjwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
        user = repo.get_user_by_id(payload["sub"])
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

scheduler = Scheduler()

@app.on_event("startup")
async def startup_event():
    logger.info("Starting API...")
    try:
        init_db()
        await scheduler.start()
        await start_bot()
    except Exception as e:
        import traceback
        logger.error(f"STARTUP FAILED: {e}")
        logger.error(traceback.format_exc())
        raise

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down API...")
    await stop_bot()
    await scheduler.stop()

# --- Pydantic Models ---
from enum import Enum

class PlatformType(str, Enum):
    instagram = "instagram"
    twitter = "twitter"
    facebook = "facebook"
    linkedin = "linkedin"
    tiktok = "tiktok"
    substack = "substack"
    gmail = "gmail"

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
    has_session: bool = False

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
    ai_instructions: Optional[str] = None
    message_template: Optional[str] = None
    account_id: Optional[str] = None

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    campaign_type: Optional[CampaignType] = None
    message_template: Optional[str] = None
    ai_instructions: Optional[str] = None
    targeting: Optional[TargetingSchema] = None
    schedule: Optional[ScheduleSchema] = None
    daily_limit: Optional[int] = None
    status: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    username: str
    token: str
    user_id: str

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
        repo.session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")
    return {"status": "ready"}

@app.delete("/api/accounts/{account_id}")
def delete_account(
    account_id: str,
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    account = repo.get_account(account_id, user["id"])
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    repo.delete_account(account_id, user["id"])
    return {"status": "deleted", "account_id": account_id}

@app.get("/api/accounts", response_model=List[AccountResponse])
def list_accounts(
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    accounts = repo.list_accounts(user["id"])
    return [
        AccountResponse(id=a.id, platform=a.platform, username=a.username, is_active=a.is_active, has_session=bool(a.session_data))
        for a in accounts
    ]

@app.post("/api/accounts", response_model=AccountResponse)
def create_account(
    account: AccountCreate,
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    new_account = DBAccount(
        id=str(uuid4()),
        user_id=user["id"],
        platform=account.platform.value,
        username=account.username,
        password=account.password,
        display_name=account.username,
        session_data=account.session_data,
        is_active=True,
        created_at=int(datetime.now().timestamp())
    )
    repo.create_account(new_account)
    return AccountResponse(
        id=new_account.id, platform=new_account.platform,
        username=new_account.username, is_active=new_account.is_active,
        has_session=bool(new_account.session_data)
    )

PLATFORM_LOGIN_URLS = {
    "instagram": lambda u: "https://www.instagram.com/accounts/login/",
    "twitter": lambda u: "https://twitter.com/i/flow/login",
    "facebook": lambda u: "https://www.facebook.com/login",
    "linkedin": lambda u: "https://www.linkedin.com/login",
    "tiktok": lambda u: "https://www.tiktok.com/login/phone-or-email/email",
    "substack": lambda u: "https://substack.com/sign-in",
    "gmail": lambda u: f"https://accounts.google.com/signin/v2/identifier?Email={u}&flowName=GlifWebSignIn&flowEntry=ServiceLogin",
}

VNC_API_HOST = "vnc-social"

def _vnc_api_url(path: str) -> str:
    return f"http://{VNC_API_HOST}:6100{path}"

async def _navigate_vnc(platform: str, account_id: str, nav_url: str):
    try:
        url = f"{_vnc_api_url('/navigate')}?url={url_quote(nav_url)}&platform={platform}&account_id={account_id}"
        await asyncio.to_thread(requests.get, url, timeout=15)
    except Exception as e:
        logger.warning(f"VNC navigate failed (background): {e}")

@app.post("/api/accounts/{account_id}/vnc-login")
async def vnc_social_login(
    account_id: str,
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    account = repo.get_account(account_id, user["id"])
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    nav_url = PLATFORM_LOGIN_URLS.get(account.platform, lambda u: f"https://{account.platform}.com/login")(account.username)
    # Navigate VNC browser to the correct platform login page in background
    asyncio.create_task(_navigate_vnc(account.platform, account_id, nav_url))
    return {
        "vnc_url": "http://153.75.247.117:6082/vnc.html",
        "platform": account.platform,
        "message": f"Open VNC and sign in to {account.platform}. Cookies will be captured automatically."
    }

@app.get("/api/accounts/{account_id}/vnc-session-status")
async def vnc_session_status(
    account_id: str,
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    account = repo.get_account(account_id, user["id"])
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        resp = requests.get(_vnc_api_url("/status"), timeout=5)
        data = resp.json()
        return {
            "login_detected": data.get("loginDetected", False),
            "has_session": bool(account.session_data),
            "platform": data.get("platform", account.platform),
            "cookies_available": data.get("cookiesFile") is not None
        }
    except:
        return {
            "login_detected": False,
            "has_session": bool(account.session_data),
            "platform": account.platform,
            "cookies_available": False
        }

@app.post("/api/accounts/{account_id}/capture-cookies")
async def capture_cookies(
    account_id: str,
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    account = repo.get_account(account_id, user["id"])
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        resp = requests.get(_vnc_api_url("/capture"), timeout=10)
        data = resp.json()
        if not data.get("success"):
            raise HTTPException(status_code=502, detail="VNC service failed to capture cookies")
        result = json.dumps(data)
    except requests.exceptions.ConnectionError:
        cookie_files = [
            f"cookies/{account_id}_cookies.json",
            f"cookies/{account.platform}_cookies.json",
        ]
        found = None
        for cf in cookie_files:
            try:
                with open(cf) as f:
                    cookies = json.load(f)
                    found = json.dumps({"success": True, "count": len(cookies)})
                    break
            except (FileNotFoundError, json.JSONDecodeError):
                continue
        if found:
            result = found
        else:
            raise HTTPException(status_code=502, detail="VNC login service not running or no cookies yet. Log in via VNC first.")
    repo.update_account_session(account_id, user["id"], result)
    return {"status": "success", "message": f"{account.platform} session saved for {account.username}"}

@app.post("/api/campaigns", response_model=CampaignResponse)
def create_campaign(
    campaign: CampaignCreate,
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    account = repo.get_account(campaign.account_id, user["id"])
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or does not belong to you")
    new_campaign = DBCampaign(
        id=str(uuid4()),
        user_id=user["id"],
        account_id=campaign.account_id,
        name=campaign.name,
        campaign_type=campaign.campaign_type.value,
        status="draft",
        targeting_json=json.dumps(campaign.targeting.model_dump()),
        message_template=campaign.message_template,
        ai_instructions=campaign.ai_instructions,
        schedule_json=json.dumps(campaign.schedule.model_dump()),
        daily_limit=campaign.daily_limit or 50,
        created_at=int(datetime.now().timestamp())
    )
    repo.create_campaign(new_campaign)
    return CampaignResponse(
        id=new_campaign.id, name=new_campaign.name,
        platform=account.platform, campaign_type=new_campaign.campaign_type,
        status=new_campaign.status, daily_limit=new_campaign.daily_limit,
        ai_instructions=new_campaign.ai_instructions,
        message_template=new_campaign.message_template,
        account_id=new_campaign.account_id,
    )

@app.get("/api/campaigns", response_model=List[CampaignResponse])
def list_campaigns(
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    campaigns = repo.list_campaigns(user["id"])
    return [
        CampaignResponse(id=c.id, name=c.name, campaign_type=c.campaign_type,
                        status=c.status, daily_limit=c.daily_limit,
                        ai_instructions=c.ai_instructions, message_template=c.message_template,
                        account_id=c.account_id, platform=c.platform)
        for c in campaigns
    ]

@app.post("/api/campaigns/{campaign_id}/start")
async def start_campaign(
    campaign_id: str,
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    campaign = repo.get_campaign(campaign_id, user["id"])
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await scheduler.start_campaign(campaign_id)
    return {"status": "started", "campaign_id": campaign_id}

@app.post("/api/campaigns/{campaign_id}/stop")
async def stop_campaign(
    campaign_id: str,
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    campaign = repo.get_campaign(campaign_id, user["id"])
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await scheduler.stop_campaign(campaign_id)
    return {"status": "stopped", "campaign_id": campaign_id}

@app.put("/api/campaigns/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    campaign_id: str,
    update: CampaignUpdate,
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    campaign = repo.get_campaign(campaign_id, user["id"])
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if update.name is not None:
        campaign.name = update.name
    if update.campaign_type is not None:
        campaign.campaign_type = update.campaign_type.value
    if update.message_template is not None:
        campaign.message_template = update.message_template
    if update.ai_instructions is not None:
        campaign.ai_instructions = update.ai_instructions
    if update.targeting is not None:
        campaign.targeting_json = json.dumps(update.targeting.model_dump())
    if update.schedule is not None:
        campaign.schedule_json = json.dumps(update.schedule.model_dump())
    if update.daily_limit is not None:
        campaign.daily_limit = update.daily_limit
    if update.status is not None:
        campaign.status = update.status
    repo.update_campaign(campaign)
    return CampaignResponse(
        id=campaign.id, name=campaign.name, platform=None,
        campaign_type=campaign.campaign_type, status=campaign.status,
        daily_limit=campaign.daily_limit,
        ai_instructions=campaign.ai_instructions,
        message_template=campaign.message_template,
        account_id=campaign.account_id,
    )

@app.delete("/api/campaigns/{campaign_id}")
def delete_campaign(
    campaign_id: str,
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    campaign = repo.get_campaign(campaign_id, user["id"])
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    repo.delete_campaign(campaign_id, user["id"])
    return {"status": "deleted", "campaign_id": campaign_id}

PLATFORM_SCRIPTS = {
    "instagram": "ig.mjs",
    "tiktok": "tiktok.mjs",
    "substack": "substack.mjs",
    "notarycafe": "nc.mjs",
    "notary-sites": "notary_sites.mjs",
    "rotary": "rotary.mjs",
}

async def _run_script(script_name: str, args: List[str] = [], timeout: int = 7200):
    try:
        proc = await asyncio.create_subprocess_exec(
            "node", script_name, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode != 0:
            logger.error(f"{script_name} failed: {stderr.decode(errors='replace')[:500]}")
        else:
            logger.info(f"{script_name} completed: {stdout.decode(errors='replace')[:500]}")
    except asyncio.TimeoutError:
        logger.warning(f"{script_name} timed out after {timeout}s")
        if proc: proc.kill()
    except Exception as e:
        logger.error(f"{script_name} error: {e}")

@app.post("/api/email-campaign/trigger")
async def trigger_email_campaign(user: dict = Depends(get_current_user)):
    asyncio.create_task(_run_script("run_campaign.mjs"))
    return {"status": "started", "message": "Email campaign launched in background"}

@app.post("/api/platforms/{platform}/trigger")
async def trigger_platform(
    platform: str,
    zip_code: Optional[str] = None,
    business_type: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    script = PLATFORM_SCRIPTS.get(platform.lower())
    if not script:
        raise HTTPException(status_code=404, detail=f"Unknown platform: {platform}")
    args = []
    if platform.lower() == "rotary":
        args = [str(500), zip_code or "", business_type or ""]
    asyncio.create_task(_run_script(script, args=args))
    return {"status": "started", "platform": platform, "message": f"{platform} automation launched in background"}

@app.post("/api/platforms/trigger-all")
async def trigger_all_platforms(user: dict = Depends(get_current_user)):
    for script in PLATFORM_SCRIPTS.values():
        asyncio.create_task(_run_script(script))
    return {"status": "started", "platforms": list(PLATFORM_SCRIPTS.keys()), "message": "All platform automations launched"}

@app.get("/api/platforms")
async def list_platforms(user: dict = Depends(get_current_user)):
    return {"platforms": list(PLATFORM_SCRIPTS.keys())}

@app.get("/api/analytics/summary")
def get_analytics(
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    return repo.get_analytics_summary(user["id"])

@app.get("/api/analytics/activity-feed")
def get_activity_feed(
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    return repo.get_activity_feed(user["id"])

@app.get("/api/analytics/audience-insights")
def get_audience_insights(
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    return repo.get_audience_insights(user["id"])

@app.post("/api/optimize/{campaign_id}")
def optimize_campaign(
    campaign_id: str,
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    campaign = repo.get_campaign(campaign_id, user["id"])
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
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

@app.post("/api/login", response_model=LoginResponse)
def login(request: LoginRequest, repo: Repository = Depends(get_repository)):
    user = repo.get_user(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    stored_hash = user['hashed_password']
    if not bcrypt.checkpw(request.password.encode('utf-8'), stored_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_token(user["id"], user["username"])
    return LoginResponse(username=request.username, token=token, user_id=user["id"])

@app.get("/api/settings")
def get_all_settings(
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    return repo.get_user_settings(user["id"])

@app.post("/api/settings")
def update_setting(
    data: Dict[str, Any],
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    for key, value in data.items():
        repo.update_user_setting(user["id"], key, str(value))
    return {"status": "success"}

@app.get("/api/settings/admin")
def get_global_settings(
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    return repo.get_all_settings()

@app.post("/api/settings/admin")
def update_global_settings(
    data: Dict[str, Any],
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    for key, value in data.items():
        repo.update_setting(key, str(value))
    return {"status": "success"}

BOT_IMAGES_DIR = "uploads/bot_images"

@app.post("/api/settings/upload-image")
async def upload_bot_image(
    file: UploadFile = File(...),
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    import os
    os.makedirs(BOT_IMAGES_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        raise HTTPException(status_code=400, detail="Only image files allowed (png, jpg, gif, webp)")
    filename = f"{uuid4()}{ext}"
    path = os.path.join(BOT_IMAGES_DIR, filename)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    stored = json.loads(repo.get_global_setting("BOT_INSTRUCTION_IMAGES", "[]"))
    stored.append(filename)
    repo.update_setting("BOT_INSTRUCTION_IMAGES", json.dumps(stored))
    return {"filename": filename, "url": f"/api/settings/images/{filename}"}

@app.get("/api/settings/images")
async def list_bot_images(
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    import os
    stored = json.loads(repo.get_global_setting("BOT_INSTRUCTION_IMAGES", "[]"))
    valid = [f for f in stored if os.path.exists(os.path.join(BOT_IMAGES_DIR, f))]
    if len(valid) != len(stored):
        repo.update_setting("BOT_INSTRUCTION_IMAGES", json.dumps(valid))
    return {"images": [{"filename": f, "url": f"/api/settings/images/{f}"} for f in valid]}

@app.get("/api/settings/images/{filename}")
async def serve_bot_image(
    filename: str,
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    import os
    path = os.path.join(BOT_IMAGES_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)

@app.delete("/api/settings/images/{filename}")
async def delete_bot_image(
    filename: str,
    repo: Repository = Depends(get_repository),
    user: dict = Depends(get_current_user)
):
    import os
    path = os.path.join(BOT_IMAGES_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
    stored = json.loads(repo.get_global_setting("BOT_INSTRUCTION_IMAGES", "[]"))
    stored = [f for f in stored if f != filename]
    repo.update_setting("BOT_INSTRUCTION_IMAGES", json.dumps(stored))
    return {"status": "deleted"}

@app.post("/api/register", response_model=LoginResponse)
def register(request: LoginRequest, repo: Repository = Depends(get_repository)):
    if repo.get_user(request.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user_id = repo.create_user(request.username, hashed)
    token = create_token(user_id, request.username)
    return LoginResponse(username=request.username, token=token, user_id=user_id)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8010)
