def test_imports():
    from app.ui.app import App
    from app.ui.components.sidebar import Sidebar
    from app.ui.pages.dashboard import DashboardPage
    assert App is not None
    assert Sidebar is not None
    assert DashboardPage is not None
