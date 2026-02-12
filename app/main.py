import logging
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime

from app.automation.scheduler import Scheduler
from app.database.connection import init_db
from app.database.repository import Repository
from app.database.models import Account as DBAccount, Campaign as DBCampaign

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API")

app = FastAPI(title="SocialGrowthAI API")

# Allow CORS for Next.js frontend (usually on port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class AccountCreate(BaseModel):
    platform: str
    username: str
    session_data: Optional[str] = None # JSON string of cookies

class AccountResponse(BaseModel):
    id: str
    platform: str
    username: str
    is_active: bool

class CampaignCreate(BaseModel):
    account_id: str
    name: str
    campaign_type: str
    targeting: Dict[str, Any]
    message_template: str
    schedule: Dict[str, Any]

class CampaignResponse(BaseModel):
    id: str
    name: str
    status: str

# --- Endpoints ---

@app.get("/")
async def root():
    return {"status": "running", "service": "SocialGrowthAI Backend"}

@app.get("/api/accounts", response_model=List[AccountResponse])
async def list_accounts():
    repo = Repository()
    try:
        accounts = repo.list_accounts()
        return [
            AccountResponse(
                id=a.id,
                platform=a.platform,
                username=a.username,
                is_active=a.is_active
            ) for a in accounts
        ]
    finally:
        repo.close()

@app.post("/api/accounts", response_model=AccountResponse)
async def create_account(account: AccountCreate):
    repo = Repository()
    try:
        new_account = DBAccount(
            id=str(uuid4()),
            platform=account.platform,
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
    finally:
        repo.close()

@app.post("/api/campaigns", response_model=CampaignResponse)
async def create_campaign(campaign: CampaignCreate):
    repo = Repository()
    try:
        new_campaign = DBCampaign(
            id=str(uuid4()),
            account_id=campaign.account_id,
            name=campaign.name,
            campaign_type=campaign.campaign_type,
            status="draft",
            targeting_json=json.dumps(campaign.targeting),
            message_template=campaign.message_template,
            schedule_json=json.dumps(campaign.schedule),
            daily_limit=50,
            created_at=int(datetime.now().timestamp())
        )
        repo.create_campaign(new_campaign)
        return CampaignResponse(
            id=new_campaign.id,
            name=new_campaign.name,
            status=new_campaign.status
        )
    finally:
        repo.close()

@app.post("/api/campaigns/{campaign_id}/start")
async def start_campaign(campaign_id: str):
    await scheduler.start_campaign(campaign_id)
    return {"status": "started", "campaign_id": campaign_id}

@app.post("/api/campaigns/{campaign_id}/stop")
async def stop_campaign(campaign_id: str):
    await scheduler.stop_campaign(campaign_id)
    return {"status": "stopped", "campaign_id": campaign_id}

@app.get("/api/analytics/summary")
async def get_analytics():
    repo = Repository()
    try:
        return repo.get_analytics_summary()
    finally:
        repo.close()

# Rust Integration Endpoint
@app.post("/api/optimize")
async def optimize_campaign(campaign_id: str):
    # This endpoint will call the Rust service
    import requests
    import os
    try:
        # Use env var or default to localhost for dev
        service_url = os.getenv("RUST_SERVICE_URL", "http://localhost:8081")
        response = requests.post(f"{service_url}/optimize", json={"campaign_id": campaign_id})
        return response.json()
    except Exception as e:
        logger.error(f"Failed to call Rust service: {e}")
        # Fallback or error
        return {"status": "error", "message": "Optimization service unavailable"}
