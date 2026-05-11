import customtkinter as ctk
import threading
import asyncio
import json
import uuid
from app.ui.pages.base import BasePage
from app.database.models import Account
from app.database.repository import Repository
from playwright.sync_api import sync_playwright

class AccountsPage(BasePage):
    def get_title(self):
        return "Accounts"

    def __init__(self, master, app_context, **kwargs):
        super().__init__(master, app_context, **kwargs)
        self.repo = Repository()

        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=10)

        self.title_lbl = ctk.CTkLabel(self.header_frame, text="Accounts", font=("Arial", 24, "bold"))
        self.title_lbl.pack(side="left")

        self.add_btn = ctk.CTkButton(self.header_frame, text="+ Add Instagram", command=lambda: self.add_account("instagram"))
        self.add_btn.pack(side="right", padx=5)

        self.add_tw_btn = ctk.CTkButton(self.header_frame, text="+ Add Twitter", command=lambda: self.add_account("twitter"))
        self.add_tw_btn.pack(side="right", padx=5)

        # List
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.refresh_list()

    def refresh_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        accounts = self.repo.list_accounts()

        for acc in accounts:
            row = ctk.CTkFrame(self.list_frame)
            row.pack(fill="x", pady=5)

            ctk.CTkLabel(row, text=acc.username, font=("Arial", 14, "bold")).pack(side="left", padx=10)
            ctk.CTkLabel(row, text=acc.platform.upper()).pack(side="left", padx=10)

            status_color = "green" if acc.is_active else "red"
            ctk.CTkLabel(row, text="Active" if acc.is_active else "Inactive", text_color=status_color).pack(side="right", padx=10)

    def add_account(self, platform):
        # We need to run this in a thread to not block UI
        dialog = ctk.CTkInputDialog(text="Enter Username (for reference):", title=f"Add {platform.title()}")
        username = dialog.get_input()
        if not username: return

        self._set_loading(True)

        t = threading.Thread(target=self._run_login_flow, args=(username, platform))
        t.start()

    def _run_login_flow(self, username, platform):
        """
        Launches browser for login.
        """
        # Create fresh repo for this thread
        thread_repo = Repository()

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()
                page = context.new_page()

                url = "https://www.instagram.com/" if platform == "instagram" else "https://twitter.com/login"
                page.goto(url)

                # Wait for user to log in.
                # Hacky but effective for desktop tool:
                # Wait for navigation to home feed
                try:
                    # Selectors for home feed/login success
                    if platform == "instagram":
                        selector = 'a[href="/"]'
                    else:
                        selector = '[data-testid="SideNav_NewTweet_Button"]'

                    page.wait_for_selector(selector, timeout=300000) # 5 mins to login
                except:
                    print("Timeout waiting for login")
                    browser.close()
                    self.after(0, lambda: self._set_loading(False))
                    return

                cookies = context.cookies()
                session_data = json.dumps(cookies)

                # Save to DB
                acc = Account(
                    id=str(uuid.uuid4()),
                    platform=platform,
                    username=username,
                    session_data=session_data,
                    is_active=True
                )
                thread_repo.create_account(acc)

                browser.close()

                self.after(0, self.refresh_list)

        except Exception as e:
            print(f"Login error: {e}")
        finally:
            self.after(0, lambda: self._set_loading(False))

    def _set_loading(self, loading):
        if loading:
            self.add_btn.configure(state="disabled")
            self.add_tw_btn.configure(state="disabled")
        else:
            self.add_btn.configure(state="normal")
            self.add_tw_btn.configure(state="normal")
