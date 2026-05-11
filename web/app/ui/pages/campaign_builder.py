import customtkinter as ctk
import json
import uuid
from app.ui.pages.base import BasePage
from app.database.models import Campaign

class CampaignBuilderPage(BasePage):
    def get_title(self):
        return "Create Campaign"

    def __init__(self, master, app_context, on_close=None, **kwargs):
        super().__init__(master, app_context, **kwargs)
        self.on_close = on_close
        self.repo = app_context.repo if hasattr(app_context, 'repo') else None

        # --- Layout ---
        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        # 1. Basic Info
        self._section("Basic Information")

        self.name_entry = self._input("Campaign Name")

        ctk.CTkLabel(self.scroll, text="Select Account").pack(anchor="w", padx=10, pady=(10,0))
        self.account_var = ctk.StringVar()
        self.account_combo = ctk.CTkComboBox(self.scroll, variable=self.account_var)
        self.account_combo.pack(fill="x", padx=10, pady=5)
        self._load_accounts()

        ctk.CTkLabel(self.scroll, text="Campaign Type").pack(anchor="w", padx=10, pady=(10,0))
        self.type_var = ctk.StringVar(value="growth")
        self.type_seg = ctk.CTkSegmentedButton(self.scroll, values=["growth", "outreach"], variable=self.type_var)
        self.type_seg.pack(fill="x", padx=10, pady=5)

        # 2. Targeting
        self._section("Targeting")
        self.tags_entry = self._input("Hashtags/Keywords (comma separated)")

        # 3. Automation Settings
        self._section("Automation Settings")
        self.limit_entry = self._input("Daily Action Limit", "50")

        # 4. Content (Outreach only)
        self._section("Message Template (Outreach Only)")
        self.template_text = ctk.CTkTextbox(self.scroll, height=100)
        self.template_text.pack(fill="x", padx=10, pady=5)
        self.template_text.insert("0.0", "Hi {username}, saw you're into {niche}...")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", command=self.cancel).pack(side="right", padx=10)
        ctk.CTkButton(btn_frame, text="Create Campaign", command=self.save).pack(side="right", padx=10)

    def _section(self, title):
        ctk.CTkLabel(self.scroll, text=title, font=("Arial", 16, "bold"), text_color="gray80").pack(anchor="w", padx=5, pady=(20, 5))
        ctk.CTkFrame(self.scroll, height=2, fg_color="gray30").pack(fill="x", padx=5, pady=(0, 10))

    def _input(self, label, default=""):
        ctk.CTkLabel(self.scroll, text=label).pack(anchor="w", padx=10, pady=(5,0))
        entry = ctk.CTkEntry(self.scroll)
        entry.pack(fill="x", padx=10, pady=5)
        if default: entry.insert(0, default)
        return entry

    def _load_accounts(self):
        if not self.repo: return
        self.accounts_map = {a.username: a.id for a in self.repo.list_accounts()}
        if self.accounts_map:
            self.account_combo.configure(values=list(self.accounts_map.keys()))
            self.account_combo.set(list(self.accounts_map.keys())[0])
        else:
            self.account_combo.configure(values=["No Accounts Found"])

    def save(self):
        if not self.repo: return

        name = self.name_entry.get()
        acc_name = self.account_combo.get()
        if acc_name not in self.accounts_map:
            print("Invalid account")
            return

        acc_id = self.accounts_map[acc_name]
        c_type = self.type_var.get()
        tags = [t.strip() for t in self.tags_entry.get().split(",") if t.strip()]
        daily_limit = int(self.limit_entry.get())
        template = self.template_text.get("0.0", "end").strip()

        camp = Campaign(
            id=str(uuid.uuid4()),
            account_id=acc_id,
            name=name,
            campaign_type=c_type,
            targeting_json=json.dumps({"tags": tags}),
            daily_limit=daily_limit,
            message_template=template if c_type == "outreach" else None
        )

        self.repo.create_campaign(camp)
        if self.on_close: self.on_close()

    def cancel(self):
        if self.on_close: self.on_close()
