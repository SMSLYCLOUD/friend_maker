import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.automation.executor import CampaignExecutor
from app.database.models import Campaign, Target, Account
from app.platforms.base import UserProfile, ActionResult

@pytest.mark.asyncio
async def test_campaign_execution():
    # Mocks
    repo = MagicMock()
    adapter = MagicMock()
    classifier = MagicMock()
    generator = MagicMock()

    # Setup Data
    camp_id = "camp1"
    acc_id = "acc1"

    repo.get_campaign.return_value = Campaign(
        id=camp_id, account_id=acc_id, name="Test", campaign_type="growth",
        targeting_json='{"tags": ["python"]}'
    )
    repo.get_account.return_value = Account(
        id=acc_id, platform="insta", username="me", session_data="enc"
    )

    # Adapter Mocks
    adapter.authenticate = AsyncMock(return_value=True)
    adapter.search_users = AsyncMock(return_value=[
        UserProfile(platform_id="u1", username="user1"),
        UserProfile(platform_id="u2", username="user2")
    ])
    adapter.follow = AsyncMock(return_value=ActionResult(success=True, action_type="follow"))

    # AI Mocks
    classifier.classify = AsyncMock(return_value={"match_score": 0.9})

    # Repository Behavior for Pending Targets
    target1 = Target(id="t1", campaign_id=camp_id, platform_user_id="u1", username="user1", status="pending")

    # Sequence:
    # 1. Loop start -> empty (trigger fetch)
    # 2. Inside if block -> [target1] (found new ones)
    # 3. Loop start (next iter) -> empty (trigger fetch again)
    # 4. Inside if block -> empty (stop)
    repo.get_pending_targets.side_effect = [[], [target1], [], []]

    executor = CampaignExecutor(repo, adapter, classifier, generator)
    executor.anti_detect.random_delay = AsyncMock() # Skip waiting

    # Run
    await executor.run_campaign(camp_id)

    # Verifications
    adapter.authenticate.assert_awaited()
    # Called twice because of the loop logic (fetched once, processed, then fetched again and found nothing)
    # adapter.search_users.assert_awaited_with("python", limit=10)
    assert adapter.search_users.call_count == 2

    # Should have added targets
    assert repo.add_target.call_count >= 1

    # Should have processed target1
    classifier.classify.assert_awaited()
    adapter.follow.assert_awaited_with("u1")

    # Should have logged action
    repo.log_action.assert_called()
    repo.update_target_status.assert_called_with("t1", "completed")
