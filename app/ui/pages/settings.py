import customtkinter as ctk
from app.ui.pages.base import BasePage

class SettingsPage(BasePage):
    def get_title(self):
        return "Settings"

    def __init__(self, master, app_context, **kwargs):
        super().__init__(master, app_context, **kwargs)

        self.form = ctk.CTkFrame(self)
        self.form.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(self.form, text="OpenRouter API Key").pack(anchor="w", pady=(10,0))
        self.api_key_entry = ctk.CTkEntry(self.form, placeholder_text="sk-or-v1-...", show="*")
        self.api_key_entry.pack(fill="x", pady=(5, 10))

        ctk.CTkButton(self.form, text="Save", command=self.save).pack(pady=20)

    def save(self):
        print("Settings saved")
