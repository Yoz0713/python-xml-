import flet as ft
from src.ui.theme import AppTheme
from src.sheets_writer import get_service_account_email, list_worksheets, get_spreadsheet_name, extract_spreadsheet_id

class SettingsPage(ft.Container):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 20
        self.bgcolor = AppTheme.BACKGROUND
        
        # --- Header ---
        self.header = ft.Column([
            ft.Text("系統設定", size=28, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_PRIMARY),
            ft.Text("管理使用者帳號與連結設定", size=14, color=AppTheme.TEXT_SECONDARY),
        ], spacing=5)
        
        # --- Profile Management ---
        self.profile_list = ft.Column(spacing=10)
        
        self.add_profile_name = ft.TextField(label="使用者名稱", height=50, expand=True)
        self.add_username = ft.TextField(label="CRM 帳號", height=50, expand=True)
        self.add_password = ft.TextField(label="CRM 密碼", password=True, can_reveal_password=True, height=50, expand=True)
        
        self.profile_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.PEOPLE, color=AppTheme.PRIMARY),
                    ft.Text("使用者帳號管理", size=18, weight=ft.FontWeight.BOLD)
                ], spacing=10),
                ft.Divider(),
                self.profile_list,
                ft.Divider(),
                ft.Text("新增帳號", size=14, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_SECONDARY),
                ft.Row([
                    self.add_profile_name,
                    self.add_username,
                    self.add_password,
                    ft.ElevatedButton("新增", on_click=self.add_profile_click, bgcolor=AppTheme.SUCCESS, color=ft.Colors.WHITE)
                ], spacing=10)
            ], spacing=15),
            padding=25,
            bgcolor=AppTheme.SURFACE,
            border_radius=12
        )
        
        # --- Google Sheets Integration ---
        self.email_display = ft.TextField(
            label="機器人 Email (複製並加入試算表共用)",
            value=get_service_account_email() or "未偵測到憑證",
            read_only=True,
            suffix=ft.IconButton(ft.Icons.COPY, on_click=self.copy_email, tooltip="複製 Email")
        )
        self.sheet_url = ft.TextField(label="Google 試算表網址", value=self.app.config.get("spreadsheet_url", ""), expand=True)
        self.sheet_dropdown = ft.Dropdown(label="選擇工作表", expand=True)
        
        saved_sheet = self.app.config.get("sheet_name", "")
        if saved_sheet:
            self.sheet_dropdown.options = [ft.dropdown.Option(saved_sheet)]
            self.sheet_dropdown.value = saved_sheet

        self.sheets_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.TABLE_CHART, color=AppTheme.SUCCESS),
                    ft.Text("Google 試算表整合", size=18, weight=ft.FontWeight.BOLD)
                ], spacing=10),
                ft.Divider(),
                self.email_display,
                ft.Row([
                    self.sheet_url,
                    ft.ElevatedButton("偵測", on_click=self.detect_sheets_click, bgcolor=AppTheme.WARNING, color=ft.Colors.WHITE)
                ], spacing=10),
                ft.Row([
                    self.sheet_dropdown,
                    ft.ElevatedButton("綁定", on_click=self.bind_sheet_click, bgcolor=AppTheme.PRIMARY, color=ft.Colors.WHITE)
                ], spacing=10)
            ], spacing=15),
            padding=25,
            bgcolor=AppTheme.SURFACE,
            border_radius=12
        )
        # --- Store Selection ---
        self.store_dropdown = ft.Dropdown(
            label="選擇門市",
            options=[ft.dropdown.Option(name) for name in self.app.store_options.keys()],
            value=self.app.store_id or "不切換 (使用預設)",
            on_change=self.on_store_change,
            expand=True
        )
        
        self.store_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.STORE, color=AppTheme.WARNING),
                    ft.Text("門市選擇", size=18, weight=ft.FontWeight.BOLD)
                ], spacing=10),
                ft.Divider(),
                ft.Text("選擇作業時使用的門市，會影響 CRM 系統的預設門市", size=13, color=AppTheme.TEXT_SECONDARY),
                self.store_dropdown
            ], spacing=15),
            padding=25,
            bgcolor=AppTheme.SURFACE,
            border_radius=12
        )
        
        # --- Layout ---
        self.content = ft.Column([
            self.header,
            ft.Container(height=20),
            self.profile_card,
            ft.Container(height=20),
            self.store_card,
            ft.Container(height=20),
            self.sheets_card
        ], scroll=ft.ScrollMode.AUTO, expand=True)
        
        self.refresh_profiles()

    def refresh_profiles(self):
        self.profile_list.controls.clear()
        profiles = self.app.profiles
        active = self.app.active_profile_name
        
        if not profiles:
            self.profile_list.controls.append(
                ft.Text("尚無帳號資料", color=AppTheme.TEXT_HINT, italic=True)
            )
        else:
            for name, data in profiles.items():
                is_active = (name == active)
                
                row = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE if is_active else ft.Icons.PERSON, 
                               color=AppTheme.SUCCESS if is_active else AppTheme.SECONDARY),
                        ft.Column([
                            ft.Text(name, weight=ft.FontWeight.BOLD),
                            ft.Text(data.get("username", ""), size=12, color=AppTheme.TEXT_SECONDARY)
                        ], spacing=2, expand=True),
                        ft.IconButton(ft.Icons.DELETE, icon_color=AppTheme.ERROR, 
                                     on_click=lambda e, n=name: self.delete_profile(n), tooltip="刪除")
                    ]),
                    padding=10,
                    border_radius=8,
                    bgcolor=AppTheme.PRIMARY_CONTAINER if is_active else AppTheme.BACKGROUND,
                    on_click=lambda e, n=name: self.activate_profile(n),
                    ink=True
                )
                self.profile_list.controls.append(row)
                
        if self.page:
            self.profile_list.update()

    def add_profile_click(self, e):
        name = self.add_profile_name.value
        user = self.add_username.value
        pwd = self.add_password.value
        if name and user:
            self.app.add_profile(name, user, pwd)
            self.add_profile_name.value = ""
            self.add_username.value = ""
            self.add_password.value = ""
            self.add_profile_name.update()
            self.add_username.update()
            self.add_password.update()
            self.refresh_profiles()
            self.app.show_snack(f"已新增帳號: {name}")

    def delete_profile(self, name):
        self.app.delete_profile(name)
        self.refresh_profiles()
        # Update dashboard badge
        self.app.dashboard_page.update_account_badge(self.app.active_profile_name)
        self.app.show_snack(f"已刪除: {name}")

    def activate_profile(self, name):
        self.app.set_active_profile(name)
        self.refresh_profiles()
        # Update dashboard badge
        self.app.dashboard_page.update_account_badge(name)
        self.app.show_snack(f"已切換至: {name}")

    def copy_email(self, e):
        self.app.page.set_clipboard(self.email_display.value)
        self.app.show_snack("已複製 Email")

    def detect_sheets_click(self, e):
        url = self.sheet_url.value
        if not url:
            self.app.show_snack("請輸入網址")
            return
            
        sheet_id = extract_spreadsheet_id(url)
        if not sheet_id:
            self.app.show_snack("無效的網址")
            return
            
        sheets = list_worksheets(sheet_id)
        if sheets:
            self.sheet_dropdown.options = [ft.dropdown.Option(s) for s in sheets]
            self.sheet_dropdown.value = sheets[0]
            self.sheet_dropdown.update()
            self.app.show_snack("已偵測到工作表")
        else:
            self.app.show_snack("無法讀取試算表，請檢查權限")

    def bind_sheet_click(self, e):
        url = self.sheet_url.value
        sheet_name = self.sheet_dropdown.value
        if url and sheet_name:
            sheet_id = extract_spreadsheet_id(url)
            title = get_spreadsheet_name(sheet_id)
            self.app.update_sheet_config(url, sheet_id, sheet_name, title)
            self.app.show_snack(f"已綁定: {title}")
    
    def on_store_change(self, e):
        """Handle store dropdown change."""
        store_name = self.store_dropdown.value
        self.app.set_store(store_name)
        # Update dashboard badge
        self.app.dashboard_page.update_store_badge(store_name)
        self.app.show_snack(f"已選擇門市: {store_name}")
