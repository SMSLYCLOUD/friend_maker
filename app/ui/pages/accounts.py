import customtkinter as ctk
import threading
import asyncio
import json
import uuid
from app.ui.pages.base import BasePage
from app.database.models import Account
from app.database.repository import Repository
from playwright.sync_api import sync_playwright

class LoginDialog(ctk.CTkToplevel):
    """Custom login dialog that asks for username/email and password sequentially."""
    
    def __init__(self, parent, platform, on_submit, on_cancel=None):
        super().__init__(parent)
        
        self.platform = platform
        self.on_submit = on_submit
        self.on_cancel = on_cancel
        
        self.title(f"Login to {platform.title()}")
        self.geometry("400x350")
        self.resizable(False, False)
        
        # Center the dialog
        self.after(100, lambda: self._center_window())
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Step tracking
        self.username_value = ""
        self.password_value = ""
        self.current_step = 0
        
        self._create_ui()
    
    def _center_window(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _create_ui(self):
        # Main container
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame, 
            text=f"Add {self.platform.title()} Account",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Progress indicator
        self.progress_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.progress_frame.pack(fill="x", pady=(0, 20))
        
        self.step1_indicator = ctk.CTkLabel(
            self.progress_frame, 
            text="● Step 1: Username/Email",
            font=ctk.CTkFont(size=12),
            text_color="#1f6aa5"
        )
        self.step1_indicator.pack(side="left", padx=5)
        
        self.step2_indicator = ctk.CTkLabel(
            self.progress_frame, 
            text="○ Step 2: Password",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.step2_indicator.pack(side="left", padx=5)
        
        # Content frame for dynamic content
        self.content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, pady=10)
        
        # Show first step
        self._show_username_step()
    
    def _show_username_step(self):
        # Clear content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Instruction
        instruction = ctk.CTkLabel(
            self.content_frame,
            text="Enter your username or email address:",
            font=ctk.CTkFont(size=14)
        )
        instruction.pack(pady=(0, 10), anchor="w")
        
        # Username entry
        self.username_entry = ctk.CTkEntry(
            self.content_frame,
            placeholder_text="username@example.com",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.username_entry.pack(fill="x", pady=(0, 20))
        self.username_entry.focus()
        
        # Bind enter key
        self.username_entry.bind("<Return>", lambda e: self._on_username_submit())
        
        # Submit button
        self.submit_btn = ctk.CTkButton(
            self.content_frame,
            text="Next",
            command=self._on_username_submit,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.submit_btn.pack(fill="x")
    
    def _on_username_submit(self):
        username = self.username_entry.get().strip()
        if not username:
            self._show_error("Please enter a username or email")
            return
        
        self.username_value = username
        self._show_password_step()
    
    def _show_password_step(self):
        # Update progress indicators
        self.step1_indicator.configure(text="● Step 1: Username/Email ✓", text_color="#2ecc71")
        self.step2_indicator.configure(text="● Step 2: Password", text_color="#1f6aa5")
        
        # Clear content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Instruction
        instruction = ctk.CTkLabel(
            self.content_frame,
            text="Enter your password:",
            font=ctk.CTkFont(size=14)
        )
        instruction.pack(pady=(0, 10), anchor="w")
        
        # Password entry
        self.password_entry = ctk.CTkEntry(
            self.content_frame,
            placeholder_text="••••••••",
            show="•",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.password_entry.pack(fill="x", pady=(0, 20))
        self.password_entry.focus()
        
        # Bind enter key
        self.password_entry.bind("<Return>", lambda e: self._on_password_submit())
        
        # Submit button
        self.submit_btn = ctk.CTkButton(
            self.content_frame,
            text="Login",
            command=self._on_password_submit,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.submit_btn.pack(fill="x")
        
        # Back button
        back_btn = ctk.CTkButton(
            self.content_frame,
            text="← Back",
            command=self._show_username_step,
            fg_color="transparent",
            border_width=1,
            height=35,
            font=ctk.CTkFont(size=12)
        )
        back_btn.pack(fill="x", pady=(10, 0))
    
    def _on_password_submit(self):
        password = self.password_entry.get()
        if not password:
            self._show_error("Please enter a password")
            return
        
        self.password_value = password
        self._submit_credentials()
    
    def _show_error(self, message):
        error_label = ctk.CTkLabel(
            self.content_frame,
            text=message,
            text_color="#e74c3c",
            font=ctk.CTkFont(size=12)
        )
        error_label.pack(pady=(5, 0))
        self.after(2000, lambda: error_label.destroy())
    
    def _submit_credentials(self):
        # Close dialog and call callback with credentials
        self.destroy()
        if self.on_submit:
            self.on_submit(self.username_value, self.password_value)
    
    def _on_cancel(self):
        self.destroy()
        if self.on_cancel:
            self.on_cancel()


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
        """Open the login dialog to collect credentials from user."""
        def on_credentials_submitted(username, password):
            self._set_loading(True)
            t = threading.Thread(target=self._run_login_flow, args=(username, password, platform))
            t.start()
        
        dialog = LoginDialog(self, platform, on_submit=on_credentials_submitted)
        dialog.wait_window()  # Wait for dialog to close

    def _run_login_flow(self, username, password, platform):
        """
        Launches browser for login using provided credentials.
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

                # Fill in credentials based on platform
                login_success = False
                try:
                    if platform == "instagram":
                        # Instagram login flow
                        self._login_instagram(page, username, password)
                    else:
                        # Twitter/X login flow
                        self._login_twitter(page, username, password)
                    
                    # Wait for successful login indicator
                    if platform == "instagram":
                        selector = 'a[href="/"]'
                    else:
                        selector = '[data-testid="SideNav_NewTweet_Button"]'

                    page.wait_for_selector(selector, timeout=300000)  # 5 mins to login
                    login_success = True
                    
                    # Get cookies after successful login
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
                    self.after(0, lambda: self._show_success_message(f"Successfully added {username}"))

                except Exception as login_error:
                    print(f"Login failed: {login_error}")
                    browser.close()
                    error_msg = str(login_error)
                    # Provide more helpful error messages
                    if "timeout" in error_msg.lower():
                        error_msg = "Login timed out. Please check your credentials and try again."
                    elif "selector" in error_msg.lower():
                        error_msg = "Could not find login form. The website may have changed."
                    self.after(0, lambda: self._show_error_message(f"Login failed: {error_msg}"))

        except Exception as e:
            print(f"Browser error: {e}")
            self.after(0, lambda: self._show_error_message(f"Error: {str(e)}"))
        finally:
            self.after(0, lambda: self._set_loading(False))

    def _login_instagram(self, page, username, password):
        """Handle Instagram login flow."""
        try:
            # Wait for login form to appear
            page.wait_for_selector('input[name="username"]', timeout=15000)
            
            # Fill username/email
            username_field = page.locator('input[name="username"]')
            username_field.fill(username)
            page.wait_for_timeout(500)  # Small delay for UX
            
            # Click next button
            next_btn = page.locator('button[type="submit"]').first
            if next_btn.is_enabled():
                next_btn.click()
            
            # Wait for password field to appear
            page.wait_for_selector('input[name="password"]', timeout=15000)
            
            # Fill password
            password_field = page.locator('input[name="password"]')
            password_field.fill(password)
            page.wait_for_timeout(500)  # Small delay for UX
            
            # Click login button
            login_btn = page.locator('button[type="submit"]').last
            if login_btn.is_enabled():
                login_btn.click()
            
            # Wait for page to load after login attempt
            page.wait_for_load_state("networkidle", timeout=30000)
            
        except Exception as e:
            raise Exception(f"Instagram login failed: {str(e)}")

    def _login_twitter(self, page, username, password):
        """Handle Twitter/X login flow."""
        try:
            # Wait for login page to load
            page.wait_for_selector('input[autocomplete="username"]', timeout=15000)
            
            # Fill username/email
            username_field = page.locator('input[autocomplete="username"]')
            username_field.fill(username)
            page.wait_for_timeout(500)  # Small delay for UX
            
            # Click next button if it exists (some flows require explicit next click)
            next_btn = page.locator('[role="button"][data-testid="openSigninNextButton"]')
            if next_btn.count() > 0 and next_btn.is_enabled():
                next_btn.click()
                # Wait for password field to appear after clicking next
                page.wait_for_selector('input[type="password"]', timeout=15000)
            
            # Fill password
            password_field = page.locator('input[type="password"]').first
            password_field.fill(password)
            page.wait_for_timeout(500)  # Small delay for UX
            
            # Click login button - try multiple selectors
            login_clicked = False
            
            # Try primary login button
            login_btn = page.locator('[role="button"][data-testid="allowAll"]')
            if login_btn.count() > 0 and login_btn.is_enabled():
                login_btn.click()
                login_clicked = True
            
            # If not found, try alternative selector
            if not login_clicked:
                login_btn = page.locator('[role="button"]').filter(has_text="Log in")
                if login_btn.count() > 0 and login_btn.is_enabled():
                    login_btn.click()
                    login_clicked = True
            
            # If still not clicked, try generic submit
            if not login_clicked:
                submit_btn = page.locator('button[type="submit"]')
                if submit_btn.count() > 0 and submit_btn.is_enabled():
                    submit_btn.click()
                    login_clicked = True
            
            # Wait for page to load after login attempt
            page.wait_for_load_state("networkidle", timeout=30000)
            
        except Exception as e:
            raise Exception(f"Twitter login failed: {str(e)}")

    def _set_loading(self, loading):
        if loading:
            self.add_btn.configure(state="disabled")
            self.add_tw_btn.configure(state="disabled")
        else:
            self.add_btn.configure(state="normal")
            self.add_tw_btn.configure(state="normal")

    def _show_success_message(self, message):
        """Show a success notification."""
        toast = ctk.CTkToplevel(self)
        toast.title("Success")
        toast.geometry("300x100")
        toast.resizable(False, False)
        toast.transient(self)
        
        label = ctk.CTkLabel(toast, text=message, font=ctk.CTkFont(size=14))
        label.pack(expand=True)
        
        toast.after(2000, toast.destroy)

    def _show_error_message(self, message):
        """Show an error notification."""
        toast = ctk.CTkToplevel(self)
        toast.title("Error")
        toast.geometry("350x100")
        toast.resizable(False, False)
        toast.transient(self)
        
        label = ctk.CTkLabel(toast, text=message, font=ctk.CTkFont(size=14), text_color="#e74c3c")
        label.pack(expand=True)
        
        toast.after(3000, toast.destroy)
