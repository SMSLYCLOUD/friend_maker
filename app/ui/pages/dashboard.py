import customtkinter as ctk
from app.ui.pages.base import BasePage

class DashboardPage(BasePage):
    def get_title(self):
        return "Dashboard"

    def __init__(self, master, app_context, **kwargs):
        super().__init__(master, app_context, **kwargs)

        # Stats Row
        self.stats_frame = ctk.CTkFrame(self)
        self.stats_frame.pack(fill="x", padx=20, pady=10)

        self.create_stat_card("Active Accounts", "3")
        self.create_stat_card("Actions Today", "125")
        self.create_stat_card("Campaigns Running", "2")

    def create_stat_card(self, title, value):
        card = ctk.CTkFrame(self.stats_frame)
        card.pack(side="left", expand=True, fill="both", padx=5, pady=5)

        ctk.CTkLabel(card, text=title, font=("Arial", 12)).pack(pady=(10,0))
        ctk.CTkLabel(card, text=value, font=("Arial", 24, "bold")).pack(pady=(0,10))
