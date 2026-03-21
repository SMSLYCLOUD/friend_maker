import customtkinter as ctk

class BasePage(ctk.CTkFrame):
    def __init__(self, master, app_context, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app_context

        self.header = ctk.CTkLabel(self, text=self.get_title(), font=ctk.CTkFont(size=24, weight="bold"))
        self.header.pack(pady=20, padx=20, anchor="w")

    def get_title(self):
        return "Page"
