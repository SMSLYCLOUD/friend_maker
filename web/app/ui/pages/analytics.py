import customtkinter as ctk
from app.ui.pages.base import BasePage
from app.database.repository import Repository

class AnalyticsPage(BasePage):
    def get_title(self):
        return "Analytics"

    def __init__(self, master, app_context, **kwargs):
        super().__init__(master, app_context, **kwargs)
        self.repo = Repository()

        # Refresh Button
        ctk.CTkButton(self.header, text="Refresh", width=80, command=self.refresh).pack(side="right", padx=10)

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.refresh()

    def refresh(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        stats = self.repo.get_analytics_summary()

        # Grid of cards
        self._stat_card("Total Actions", str(stats["total_actions"]), 0, 0)
        self._stat_card("Actions Today", str(stats["today_actions"]), 0, 1)
        self._stat_card("Success Rate", f"{stats['success_rate']}%", 0, 2)

        # Simple progress bar for success rate
        bar_frame = ctk.CTkFrame(self.content_frame)
        bar_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=20)

        ctk.CTkLabel(bar_frame, text="Success Rate Visualization").pack(anchor="w", padx=10, pady=5)
        bar = ctk.CTkProgressBar(bar_frame)
        bar.pack(fill="x", padx=10, pady=(0, 10))
        bar.set(stats["success_rate"] / 100.0)

    def _stat_card(self, title, value, r, c):
        card = ctk.CTkFrame(self.content_frame)
        card.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")
        self.content_frame.grid_columnconfigure(c, weight=1)

        ctk.CTkLabel(card, text=title, font=("Arial", 14), text_color="gray").pack(pady=(15, 0))
        ctk.CTkLabel(card, text=value, font=("Arial", 32, "bold")).pack(pady=(5, 15))
