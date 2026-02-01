import pytest
from unittest.mock import AsyncMock, MagicMock
from app.platforms.twitter import TwitterAdapter

@pytest.fixture
def mock_page():
    page = MagicMock()
    page.context = MagicMock()
    page.context.cookies = AsyncMock(return_value=[])
    page.context.add_cookies = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()

    return page

@pytest.mark.asyncio
async def test_twitter_auth(mock_page):
    adapter = TwitterAdapter(mock_page)
    success = await adapter.authenticate('[{"name": "auth_token", "value": "123"}]')
    assert success is True
    mock_page.goto.assert_called_with("https://twitter.com/home")

@pytest.mark.asyncio
async def test_twitter_search(mock_page):
    adapter = TwitterAdapter(mock_page)

    # Mock locator for users
    cell = MagicMock()
    cell.inner_text = AsyncMock(return_value="Display Name\n@username\nBio")

    mock_page.locator.return_value.all.return_value = [cell]

    results = await adapter.search_users("python")

    assert len(results) > 0
    assert results[0].username == "username"
