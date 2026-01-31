import customtkinter as ctk
from typing import Callable

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_navigate: Callable[[str], None], **kwargs):
        super().__init__(master, width=200, corner_radius=0, **kwargs)
        self.on_navigate = on_navigate

        self.logo_label = ctk.CTkLabel(self, text="SocialGrowthAI", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.pack(padx=20, pady=(20, 10))

        self.buttons = {}
        self.create_nav_button("Dashboard")
        self.create_nav_button("Accounts")
        self.create_nav_button("Campaigns")
        self.create_nav_button("Settings")

    def create_nav_button(self, text):
        btn = ctk.CTkButton(
            self,
            text=text,
            command=lambda: self.on_navigate(text),
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w"
        )
        btn.pack(pady=5, padx=10, fill="x")
        self.buttons[text] = btn
