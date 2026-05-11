import pytest
import uuid
import os
from app.database.connection import init_db, DB_PATH
from app.database.repository import Repository
from app.database.models import Account, Campaign, Target, ActionLog

@pytest.fixture
def repo():
    # Setup
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    r = Repository()
    yield r
    # Teardown
    r.close()
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def test_account_crud(repo):
    acc_id = str(uuid.uuid4())
    acc = Account(
        id=acc_id,
        platform="instagram",
        username="testuser",
        session_data="super_secret_cookie"
    )

    # Create
    repo.create_account(acc)

    # Read
    fetched = repo.get_account(acc_id)
    assert fetched is not None
    assert fetched.username == "testuser"
    assert fetched.session_data == "super_secret_cookie" # Should be decrypted automatically

    # Update Session
    repo.update_account_session(acc_id, "new_cookie")
    updated = repo.get_account(acc_id)
    assert updated.session_data == "new_cookie"

def test_campaign_crud(repo):
    acc_id = str(uuid.uuid4())
    repo.create_account(Account(id=acc_id, platform="insta", username="u"))

    camp_id = str(uuid.uuid4())
    camp = Campaign(
        id=camp_id,
        account_id=acc_id,
        name="Test Camp",
        campaign_type="growth"
    )

    repo.create_campaign(camp)
    fetched = repo.get_campaign(camp_id)
    assert fetched.name == "Test Camp"

def test_target_flow(repo):
    acc_id = str(uuid.uuid4())
    repo.create_account(Account(id=acc_id, platform="insta", username="u"))
    camp_id = str(uuid.uuid4())
    repo.create_campaign(Campaign(id=camp_id, account_id=acc_id, name="C", campaign_type="T"))

    t_id = str(uuid.uuid4())
    target = Target(
        id=t_id,
        campaign_id=camp_id,
        platform_user_id="12345",
        username="target_user"
    )

    repo.add_target(target)

    pending = repo.get_pending_targets(camp_id)
    assert len(pending) == 1
    assert pending[0].username == "target_user"

    repo.update_target_status(t_id, "processed", ai_score=0.95)
    pending_after = repo.get_pending_targets(camp_id)
    assert len(pending_after) == 0

def test_logging(repo):
    log_id = str(uuid.uuid4())
    log = ActionLog(
        id=log_id,
        action_type="follow",
        success=True
    )
    repo.log_action(log)

    # Simple verify via raw sql
    cursor = repo.conn.execute("SELECT count(*) FROM action_logs")
    assert cursor.fetchone()[0] == 1
