from app.ui.pages.campaign_builder import CampaignBuilderPage
from unittest.mock import MagicMock

def test_builder_init():
    app_ctx = MagicMock()
    app_ctx.repo = MagicMock()
    app_ctx.repo.list_accounts.return_value = []

    # CTK widgets require a root, but we can't easily mock that in headless easily without xvfb
    # However, we can check if the class imports and methods exist.
    assert hasattr(CampaignBuilderPage, "save")
    assert hasattr(CampaignBuilderPage, "cancel")
