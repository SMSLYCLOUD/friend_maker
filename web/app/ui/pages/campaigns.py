import customtkinter as ctk
import uuid
from app.ui.pages.base import BasePage
from app.database.models import Campaign
from app.database.repository import Repository

class CampaignsPage(BasePage):
    def get_title(self):
        return "Campaigns"

    def __init__(self, master, app_context, **kwargs):
        super().__init__(master, app_context, **kwargs)
        self.repo = Repository()

        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(self.header_frame, text="Campaigns", font=("Arial", 24, "bold")).pack(side="left")

        self.add_btn = ctk.CTkButton(self.header_frame, text="+ New Campaign", command=self.show_create_dialog)
        self.add_btn.pack(side="right")

        # List
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.refresh()

    def refresh(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        campaigns = self.repo.conn.execute("SELECT * FROM campaigns").fetchall()

        for row in campaigns:
            c_data = dict(row)
            camp = Campaign(**c_data)

            card = ctk.CTkFrame(self.list_frame)
            card.pack(fill="x", pady=5)

            ctk.CTkLabel(card, text=camp.name, font=("Arial", 14, "bold")).pack(side="left", padx=10)
            ctk.CTkLabel(card, text=camp.campaign_type).pack(side="left", padx=10)
            ctk.CTkLabel(card, text=camp.status).pack(side="left", padx=10)

            # Action Buttons
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(side="right", padx=10)

            ctk.CTkButton(btn_frame, text="Run", width=60,
                          command=lambda id=camp.id: self.run_campaign(id)).pack(side="left", padx=2)
            ctk.CTkButton(btn_frame, text="Stop", width=60, fg_color="red",
                          command=lambda id=camp.id: self.stop_campaign(id)).pack(side="left", padx=2)

    def show_create_dialog(self):
        self.app.show_page("CampaignBuilder")

    def run_campaign(self, campaign_id):
        print(f"Running {campaign_id}")
        camp = self.repo.get_campaign_by_id(campaign_id)
        if camp:
            self.app.run_async_task(self.app.scheduler.start_campaign(campaign_id, camp.user_id))

    def stop_campaign(self, campaign_id):
        print(f"Stopping {campaign_id}")
        self.app.run_async_task(self.app.scheduler.stop_campaign(campaign_id))
