import customtkinter as ctk
import asyncio
import threading
from app.ui.components.sidebar import Sidebar
from app.ui.pages import DashboardPage, AccountsPage, CampaignsPage, SettingsPage
from app.ui.theme import Colors
from app.automation.scheduler import Scheduler

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SocialGrowthAI")
        self.geometry("1000x600")

        # Theme config
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Backend components
        self.scheduler = Scheduler()

        # Grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = Sidebar(self, on_navigate=self.show_page)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Main Area
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew")

        # Pages
        self.pages = {}
        self.current_page = None

        self.init_pages()
        self.show_page("Dashboard")

        # Start Scheduler Loop in background thread if needed
        # Or just have it ready.
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self._run_async_loop, daemon=True).start()

    def _run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_async_task(self, coro):
        asyncio.run_coroutine_threadsafe(coro, self.loop)

    def init_pages(self):
        # We can pass self (App) as context to pages
        self.pages["Dashboard"] = DashboardPage(self.main_area, self)
        self.pages["Accounts"] = AccountsPage(self.main_area, self)
        self.pages["Campaigns"] = CampaignsPage(self.main_area, self)
        self.pages["Settings"] = SettingsPage(self.main_area, self)

    def show_page(self, name):
        if self.current_page:
            self.current_page.pack_forget()

        if name in self.pages:
            self.current_page = self.pages[name]
            self.current_page.pack(fill="both", expand=True)
            if hasattr(self.current_page, 'refresh'):
                self.current_page.refresh()

    def run(self):
        self.mainloop()
