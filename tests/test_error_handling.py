import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.automation.executor import CampaignExecutor
from app.database.models import Campaign, Target, Account
from app.platforms.base import UserProfile, ActionResult

@pytest.mark.asyncio
async def test_executor_error_handling():
    # Mocks
    repo = MagicMock()
    adapter = MagicMock()

    # Setup Data
    camp_id = "camp1"
    repo.get_campaign.return_value = Campaign(id=camp_id, account_id="a", name="T", campaign_type="growth")
    repo.get_account.return_value = Account(id="a", platform="i", username="u", session_data="e")

    # Adapter throws error
    adapter.authenticate = AsyncMock(return_value=True)
    # _process_target calls adapter.follow which throws
    adapter.follow = AsyncMock(side_effect=Exception("Network Down"))
    adapter.search_users = AsyncMock(return_value=[]) # Handle fetch call

    # Target
    target = Target(id="t1", campaign_id=camp_id, platform_user_id="u", username="u", status="pending")
    # 1. [target] -> Process (fail)
    # 2. [] -> Fetch -> [] (search returns empty) -> Break
    repo.get_pending_targets.side_effect = [[target], [], []]

    executor = CampaignExecutor(repo, adapter)
    executor.anti_detect.trigger_cooldown = AsyncMock()
    executor.anti_detect.random_delay = AsyncMock()

    # Run
    await executor.run_campaign(camp_id)

    # Verify cooldown triggered
    executor.anti_detect.trigger_cooldown.assert_awaited()

    # Verify logged
    repo.log_action.assert_called()
    # Check that we logged a failure
    assert repo.update_target_status.call_args[0][1] == "failed"
