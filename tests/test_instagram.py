import pytest
from unittest.mock import AsyncMock, MagicMock
from app.platforms.instagram import InstagramAdapter

@pytest.fixture
def mock_page():
    page = MagicMock() # Page methods like get_by_role are sync

    # Context needs to be async or match usage
    # page.context.cookies() is async
    page.context = MagicMock()
    page.context.cookies = AsyncMock(return_value=[])
    page.context.add_cookies = AsyncMock()

    # page.goto is async
    page.goto = AsyncMock()
    # page.wait_for_selector is async
    page.wait_for_selector = AsyncMock()
    # page.wait_for_timeout is async
    page.wait_for_timeout = AsyncMock()
    # page.query_selector_all is async
    page.query_selector_all = AsyncMock(return_value=[])

    return page

@pytest.mark.asyncio
async def test_auth_success(mock_page):
    adapter = InstagramAdapter(mock_page)

    success = await adapter.authenticate('[{"name": "sessionid", "value": "123"}]')

    assert success is True
    mock_page.context.add_cookies.assert_called_once()
    mock_page.goto.assert_called_with("https://www.instagram.com/")

@pytest.mark.asyncio
async def test_follow(mock_page):
    adapter = InstagramAdapter(mock_page)

    # Setup mock for "Follow" button
    # get_by_role returns a locator synchronously
    btn_locator = MagicMock()
    # count() on locator is async
    btn_locator.count = AsyncMock(return_value=1)
    btn_locator.click = AsyncMock()

    mock_page.get_by_role.return_value = btn_locator

    result = await adapter.follow("jules")

    assert result.success is True, f"Error: {result.error}"
    assert result.action_type == "follow"
    btn_locator.click.assert_called_once()

@pytest.mark.asyncio
async def test_search(mock_page):
    adapter = InstagramAdapter(mock_page)

    # Mock search icon found
    search_icon = MagicMock()
    search_icon.count = AsyncMock(return_value=1)
    search_icon.click = AsyncMock()

    # Mock input box
    input_box = MagicMock()
    input_box.fill = AsyncMock()

    # Helper to return different mocks based on call
    def get_by_role_side_effect(role, name=None, **kwargs):
        if name == "Search":
            return search_icon
        return MagicMock() # Return dummy locator for others

    mock_page.get_by_role.side_effect = get_by_role_side_effect
    mock_page.get_by_placeholder.return_value = input_box

    # Mock query_selector_all
    link_mock = MagicMock()
    link_mock.get_attribute = AsyncMock(return_value="/someuser/")
    mock_page.query_selector_all.return_value = [link_mock]

    results = await adapter.search_users("python")

    assert len(results) > 0
    assert results[0].username == "someuser"
