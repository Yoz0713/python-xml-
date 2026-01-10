"""
大樹聽中行政自動化 - Flet GUI
Modern Material Design 3 interface for hearing assessment automation.
"""
import flet as ft
import asyncio
import os
import json
import base64
import threading
from typing import Optional, Dict, Any, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.parser import parse_noah_xml, get_available_sessions
from src.automation import HearingAutomation, run_automation_sync
from src.config import FIELD_MAP
from src.sheets_writer import (
    is_sheets_available, 
    get_service_account_email, 
    extract_spreadsheet_id,
    list_worksheets,
    append_row_to_sheet,
    build_row_data,
    calculate_pta,
    get_spreadsheet_name,  # Import new function
)

# Config file path in user's AppData
CONFIG_DIR = os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'HearingAutomation')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')


def _encode_password(password: str) -> str:
    """Encode password with Base64."""
    return base64.b64encode(password.encode('utf-8')).decode('utf-8')


def _decode_password(encoded: str) -> str:
    """Decode Base64 encoded password."""
    try:
        return base64.b64decode(encoded.encode('utf-8')).decode('utf-8')
    except:
        return ""


def load_config() -> dict:
    """Load config from file."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {"accounts": {}, "last_username": "", "last_store": "", "last_folder": ""}


def save_config(config: dict):
    """Save config to file."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Config] Error saving config: {e}")


class XMLFileHandler(FileSystemEventHandler):
    """Watch for new XML files."""
    
    def __init__(self, callback):
        self.callback = callback
        self.last_path = None
        self.last_time = 0
    
    def _process_event(self, event):
        if event.is_directory:
            return
        
        filename = event.src_path
        if not filename.lower().endswith('.xml'):
            return
            
        import time
        current_time = time.time()
        
        # Simple debounce (avoid duplicate events within 1 second)
        if filename == self.last_path and (current_time - self.last_time) < 1.0:
            return
            
        self.last_path = filename
        self.last_time = current_time
        self.callback(filename)

    def on_created(self, event):
        self._process_event(event)
        
    def on_modified(self, event):
        self._process_event(event)
        
    def on_moved(self, event):
        """Handle file moved INTO the monitored folder."""
        if event.is_directory:
            return
        
        # Use dest_path since that's where the file ended up
        filename = event.dest_path
        if not filename.lower().endswith('.xml'):
            return
        
        import time
        current_time = time.time()
        
        # Apply same debounce logic
        if filename == self.last_path and (current_time - self.last_time) < 1.0:
            return
        
        self.last_path = filename
        self.last_time = current_time
        self.callback(filename)


class HearingApp:
    """Main Flet Application."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.setup_page()
        
        # State
        self.detected_file: Optional[str] = None
        self.xml_data: Dict[str, Any] = {}
        self.monitoring = False
        self.processed_files_history = {}  # Map path -> mtime
        self.processed_files_history = {}  # Map path -> mtime
        self.processing_lock = threading.Lock()
        
        # Queue System
        self.pending_files: List[str] = []
        self.current_file: Optional[str] = None
        
        # Config
        loaded_config = load_config()
        self.profiles = loaded_config.get("profiles", {})
        last_profile_name = loaded_config.get("last_profile", "")
        
        # Default config
        self.config = {
            "url": "https://crm.greattree.com.tw/",
            "username": "",
            "password": "",
            "store_id": ""
        }
        
        # Load active profile if exists
        self.active_profile_name = None
        if last_profile_name and last_profile_name in self.profiles:
            p = self.profiles[last_profile_name]
            self.active_profile_name = last_profile_name
            self.config["username"] = p.get("username", "")
            self.config["password"] = _decode_password(p.get("password", ""))
            self.config["store_id"] = p.get("store_id", "")
            
        # Watch path
        self.watch_path = loaded_config.get("last_folder", "")
        self.accounts = {} # Legacy support container, unused now
        
        # Load Google Sheets config from global config
        self.config["spreadsheet_url"] = loaded_config.get("spreadsheet_url", "")
        self.config["spreadsheet_id"] = loaded_config.get("spreadsheet_id", "")
        self.config["sheet_name"] = loaded_config.get("sheet_name", "")
        self.config["spreadsheet_title"] = loaded_config.get("spreadsheet_title", "") # New: Spreadsheet title
        
        # Store options
        self.store_options = {
            "不切換 (使用預設)": "",
            "桃園藝文店": "0O146270501766340937",
            "龜山萬壽店": "0O303359038470254289",
            "內壢忠孝二店": "0O309358019937740140",
            "中壢環東店": "0O311663907407279810",
            "彰化員林大同店": "0P345691397366329983",
            "湖口成長店": "0O312542441306802027",
            "北屯崇德店": "0O312543766542134683",
            "西屯福科店": "0P343591528669372377",
            "竹北中興店": "0P343592174119614845",
            "羅東倉前店": "0P345513608514105513",
        }
        
        # FilePicker
        self.file_picker = ft.FilePicker(on_result=self.on_dialog_result)
        self.page.overlay.append(self.file_picker)
        
        # Initialize header sheets status container
        self.header_sheets_status = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.WARNING, size=16, color=ft.Colors.ORANGE),
                ft.Text("試算表未連線", size=12, color=ft.Colors.ORANGE),
            ], spacing=5, alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.ORANGE),
            tooltip="Google Sheets 尚未綁定或 credentials.json 遺失",
            visible=True,
        )
        
        self.build_ui()
    
    def setup_page(self):
        """Configure page settings."""
        self.page.title = "大樹聽中行政自動化"
        self.page.window.width = 1200
        self.page.window.height = 800
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.theme = ft.Theme(
            color_scheme_seed=ft.Colors.BLUE,
            use_material3=True,
        )
        self.page.padding = 0
    
    def build_ui(self):
        """Build the main UI."""
        # === Status Indicator (with animation support) ===
        self.status_icon = ft.Icon(ft.Icons.STOP_CIRCLE, color=ft.Colors.GREY, size=20)
        self.status_text = ft.Text("未啟動", size=14, color=ft.Colors.GREY)
        self.status_container = ft.Container(
            content=ft.Row([self.status_icon, self.status_text], spacing=8),
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            border_radius=20,
            bgcolor=ft.Colors.GREY_800,
        )
        
        # === Google Sheets Status Badge ===
        # This will be updated by _update_sheets_badge
        
        # === Header Bar Dropdowns ===
        # Account selector in header
        self.header_account_text = ft.Text(
            f"👤 {self.active_profile_name or '未選擇'}", 
            size=13, 
            color=ft.Colors.WHITE
        )
        self.header_account_btn = ft.Container(
            content=ft.Row([
                self.header_account_text,
                ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=16, color=ft.Colors.WHITE),
            ], spacing=2),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=6,
            bgcolor=ft.Colors.GREY_700,
            on_click=self._show_account_menu,
            ink=True,
        )
        
        # Store selector in header
        store_display = self.config.get("store_id") or "不切換"
        self.header_store_text = ft.Text(
            f"🏪 {store_display}", 
            size=13, 
            color=ft.Colors.WHITE
        )
        self.header_store_btn = ft.Container(
            content=ft.Row([
                self.header_store_text,
                ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=16, color=ft.Colors.WHITE),
            ], spacing=2),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=6,
            bgcolor=ft.Colors.GREY_700,
            on_click=self._show_store_menu,
            ink=True,
        )
        
        # Create tabs
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="📡 即時監控", content=self.build_monitor_tab()),
                ft.Tab(text="⚙️ 設定", content=self.build_settings_tab()),
            ],
            expand=True,
        )
        
        # Main layout
        self.page.add(
            ft.Container(
                content=ft.Column([
                    # Top bar with status
                    ft.Container(
                        content=ft.Row([
                            ft.Row([
                                ft.Icon(ft.Icons.HEARING, size=28, color=ft.Colors.BLUE),
                                ft.Text("大樹聽中行政自動化", size=20, weight=ft.FontWeight.BOLD),
                            ], spacing=10),
                            ft.Container(expand=True),
                            self.status_container,
                        ]),
                        padding=ft.padding.symmetric(horizontal=20, vertical=12),
                        bgcolor=ft.Colors.GREY_900,
                    ),
                    # User info bar with dropdown selectors
                    ft.Container(
                        content=ft.Row([
                            self.header_account_btn,
                            ft.Container(width=12),
                            self.header_store_btn,
                            ft.Container(expand=True),
                            self.header_sheets_status, # Use the new header sheets status
                        ], spacing=5),
                        padding=ft.padding.symmetric(horizontal=20, vertical=8),
                        bgcolor=ft.Colors.GREY_800,
                        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.GREY_700)),
                    ),
                    # Tabs
                    self.tabs,
                ], spacing=0),
                expand=True,
            )
        )
        
        # Sync header with loaded config
        self._update_header_selectors()
        self._update_sheets_badge() # Update sheets badge after UI is built
        
        # Check first-time setup
        self._check_first_time_setup()
    
    def build_monitor_tab(self) -> ft.Container:
        """Build the real-time monitor tab."""
        # Folder selector
        initial_folder_text = self.watch_path if self.watch_path else "選擇監控資料夾..."
        self.folder_path_text = ft.Text(initial_folder_text, size=13, color=ft.Colors.WHITE if self.watch_path else ft.Colors.GREY)
        
        self.monitor_btn = ft.ElevatedButton(
            text="▶️ 開始監控",
            on_click=self.toggle_monitoring,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE,
            ),
        )
        
        # Patient card
        self.patient_name = ft.Text("等待偵測 XML 檔案...", size=18, weight=ft.FontWeight.BOLD)
        self.patient_info = ft.Text("", size=13, color=ft.Colors.GREY)
        
        self.process_btn = ft.ElevatedButton(
            text="⚙️ 設定並上傳",
            on_click=self.open_wizard,
            disabled=True,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREEN,
            ),
        )
        
        patient_card = ft.Card(
            content=ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.PERSON, size=40),
                    ft.Column([
                        self.patient_name,
                        self.patient_info,
                    ], spacing=2, expand=True),
                    self.process_btn,
                ]),
                padding=20,
            ),
        )
        
        # XML Preview
        self.xml_preview = ft.Text("", size=12, selectable=True)
        
        # Log area
        self.log_list = ft.ListView(expand=True, spacing=2, auto_scroll=True)
        
        # Right Side: Pending Queue
        self.pending_list_view = ft.ListView(expand=True, spacing=5)
        
        return ft.Container(
            content=ft.Row([
                # Left Column: Main Content (expand=7)
                ft.Container(
                    content=ft.Column([
                        # Control bar
                        ft.Card(
                            content=ft.Container(
                                content=ft.Row([
                                    # Clickable folder selector area
                                    ft.Container(
                                        content=ft.Row([
                                            ft.Icon(ft.Icons.FOLDER_OPEN, size=20),
                                            ft.Container(content=self.folder_path_text, expand=True),
                                        ], spacing=10),
                                        on_click=self.pick_folder,
                                        expand=True,
                                        ink=True,
                                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                                        border_radius=5,
                                        tooltip="點擊選擇監控資料夾",
                                    ),
                                    self.monitor_btn,
                                ]),
                                padding=10,
                            ),
                        ),
                        # Patient card
                        patient_card,
                        # Content area (Tabs)
                        ft.Container(
                            content=ft.Tabs(
                                selected_index=0,
                                tabs=[
                                    ft.Tab(text="📄 XML 預覽", content=ft.Column([self.xml_preview], scroll=ft.ScrollMode.AUTO)),
                                    ft.Tab(text="📝 執行日誌", content=self.log_list),
                                ],
                                expand=True,
                            ),
                            expand=True,
                            bgcolor=ft.Colors.GREY_900,
                            border_radius=10,
                            padding=10,
                        ),
                    ]),
                    expand=7,
                    padding=10,
                ),
                # Right Column: Queue Sidebar (expand=3)
                ft.Container(
                   content=ft.Column([
                       ft.Text("⏳ 待處理清單", weight=ft.FontWeight.BOLD, size=16),
                       ft.Divider(),
                       self.pending_list_view,
                   ]),
                   expand=3,
                   bgcolor=ft.Colors.GREY_900,
                   border_radius=10,
                   padding=10,
                   margin=ft.margin.only(top=10, bottom=10, right=10),
                )
            ]),
            padding=0,
        )
    
    def build_settings_tab(self) -> ft.Container:
        """Build the settings tab with Profile Management."""
        
        
        # --- Section 2A: Add New Account ---

        # --- Section 2A: Add New Account ---
        self.add_profile_name_field = ft.TextField(
            label="👤 使用者名稱 (例如: 王小明)",
            hint_text="輸入自定義名稱以供識別",
            prefix_icon=ft.Icons.BADGE,
        )
        
        self.add_username_field = ft.TextField(
            label="CRM 帳號 (工號)",
            prefix_icon=ft.Icons.PERSON,
        )
        
        self.add_password_field = ft.TextField(
            label="CRM 密碼",
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK,
        )

        self.add_profile_btn = ft.ElevatedButton(
            "➕ 新增帳號",
            icon=ft.Icons.ADD,
            on_click=self._add_new_profile,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREEN,
                padding=15,
            )
        )
        
        # --- Section 2B: Edit Existing Account (Collapsible) ---
        self.editing_profile_name = None  # Track which profile is being edited
        
        self.edit_profile_name_field = ft.TextField(
            label="👤 使用者名稱",
            prefix_icon=ft.Icons.BADGE,
            read_only=True,  # Name cannot be changed
            bgcolor=ft.Colors.GREY_800,
        )
        
        self.edit_username_field = ft.TextField(
            label="CRM 帳號 (工號)",
            prefix_icon=ft.Icons.PERSON,
        )
        
        self.edit_password_field = ft.TextField(
            label="CRM 密碼",
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK,
        )
        
        self.cancel_edit_btn = ft.TextButton(
            "取消",
            icon=ft.Icons.CLOSE,
            on_click=self._cancel_edit,
        )

        self.save_edit_btn = ft.ElevatedButton(
            "💾 儲存變更",
            icon=ft.Icons.SAVE,
            on_click=self._save_edit_profile,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE,
                padding=15,
            )
        )
        
        # Collapsible edit section container
        self.edit_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.EDIT, color=ft.Colors.ORANGE),
                    ft.Text("編輯帳號", size=16, weight=ft.FontWeight.BOLD),
                ]),
                ft.Divider(),
                self.edit_profile_name_field,
                self.edit_username_field,
                self.edit_password_field,
                ft.Container(height=10),
                ft.Row([
                    self.cancel_edit_btn,
                    ft.Container(expand=True),
                    self.save_edit_btn,
                ]),
            ], spacing=12),
            padding=20,
            border=ft.border.all(2, ft.Colors.ORANGE),
            border_radius=10,
            bgcolor=ft.Colors.GREY_900,
            visible=False,  # Hidden by default
        )
        
        # Keep old fields for compatibility but they won't be used in UI
        self.profile_name_field = self.add_profile_name_field
        self.username_field = self.add_username_field
        self.password_field = self.add_password_field
        self.save_profile_btn = self.add_profile_btn
        
        # --- Section 3: Google Sheets Integration ---
        self.sheets_url_field = ft.TextField(
            label="試算表網址 (Google Sheets URL)",
            hint_text="貼上試算表的網址",
            prefix_icon=ft.Icons.LINK,
            value=self.config.get("spreadsheet_url", ""),
        )
        
        # Worksheet dropdown (initially empty)
        self.sheets_worksheet_dropdown = ft.Dropdown(
            label="選擇工作表",
            options=[],
            prefix_icon=ft.Icons.TABLE_VIEW,
            visible=False,  # Hidden until worksheets are loaded
        )
        
        self.detect_worksheets_btn = ft.ElevatedButton(
            "🔍 偵測工作表",
            icon=ft.Icons.SEARCH,
            on_click=self._detect_worksheets,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.ORANGE,
                padding=15,
            )
        )
        
        self.save_sheets_btn = ft.ElevatedButton(
            "🔗 綁定試算表",
            icon=ft.Icons.LINK,
            on_click=self._save_sheets_config,
            visible=False,  # Hidden until worksheet is selected
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE,
                padding=15,
            )
        )
        
        # Status text for binding
        current_sheet = self.config.get("sheet_name", "")
        current_id = self.config.get("spreadsheet_id", "")
        current_title = self.config.get("spreadsheet_title", "")
        status_msg = f"✅ 已綁定: {current_title} ({current_sheet})" if current_id and current_sheet else "💡 尚未綁定試算表"
        self.sheets_status_text = ft.Text(status_msg, size=12, color=ft.Colors.GREY)
        
        # If already bound, show worksheet dropdown and save button initialized
        if current_id and current_sheet:
            # Add the saved sheet as an option so it displays correctly
            self.sheets_worksheet_dropdown.options = [ft.dropdown.Option(current_sheet)]
            self.sheets_worksheet_dropdown.value = current_sheet
            self.sheets_worksheet_dropdown.visible = True
            self.save_sheets_btn.visible = True
        

        
        return ft.Container(
            content=ft.Column([
                # Card 1: Account List
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.PEOPLE, color=ft.Colors.CYAN),
                                ft.Text("已儲存的帳號", size=18, weight=ft.FontWeight.BOLD),
                            ]),
                            ft.Divider(),
                            self._build_account_list(),
                            # Collapsible Edit Section (below account list)
                            self.edit_section,
                        ], spacing=10),
                        padding=20,
                    ),
                    color=ft.Colors.GREY_900,
                ),
                
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                
                # Card 2: Add New Account
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.PERSON_ADD, color=ft.Colors.GREEN),
                                ft.Text("新增帳號", size=18, weight=ft.FontWeight.BOLD),
                            ]),
                            ft.Divider(),
                            self.add_profile_name_field,
                            self.add_username_field,
                            self.add_password_field,
                            ft.Container(height=10),
                            self.add_profile_btn,
                        ], spacing=15),
                        padding=30,
                    ),
                ),
                
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                
                # Card 3: Google Sheets Integration
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.TABLE_CHART, color=ft.Colors.GREEN),
                                ft.Text("Google 試算表整合", size=18, weight=ft.FontWeight.BOLD),
                            ]),
                            ft.Divider(),
                            # Service Account Email Display
                            ft.Text("機器人 Email (請將此 Email 加入試算表的編輯者):", size=12, color=ft.Colors.GREY),
                            ft.Row([
                                ft.Text(
                                    get_service_account_email() or "⚠️ 尚未設定 credentials.json",
                                    size=13,
                                    selectable=True,
                                    color=ft.Colors.CYAN if get_service_account_email() else ft.Colors.ORANGE,
                                ),
                                ft.IconButton(
                                    ft.Icons.COPY,
                                    tooltip="複製 Email",
                                    on_click=self._copy_service_email,
                                ),
                            ]),
                            ft.Container(height=10),
                            # Step 1: Spreadsheet URL Input
                            self.sheets_url_field,
                            ft.Container(height=5),
                            # Step 2: Detect Worksheets
                            self.detect_worksheets_btn,
                            ft.Container(height=10),
                            # Step 3: Select Worksheet
                            self.sheets_worksheet_dropdown,
                            ft.Container(height=10),
                            # Step 4: Bind
                            self.save_sheets_btn,
                            ft.Container(height=10),
                            # Status display
                            self.sheets_status_text,
                        ], spacing=10),
                        padding=30,
                    ),
                    color=ft.Colors.GREY_900,
                ),
            ], scroll=ft.ScrollMode.AUTO),
            padding=20,
            expand=True,
        )
    
    def _build_account_list(self):
        """Build a list of saved accounts for display in settings."""
        self.account_list_container = ft.Column(spacing=8)
        self._refresh_account_list()
        return self.account_list_container
    
    def _refresh_account_list(self):
        """Refresh the account list display."""
        if not hasattr(self, 'account_list_container'):
            return
            
        self.account_list_container.controls.clear()
        
        if not self.profiles:
            self.account_list_container.controls.append(
                ft.Text("尚未儲存任何帳號", size=13, color=ft.Colors.GREY, italic=True)
            )
        else:
            for name, profile in self.profiles.items():
                is_active = name == self.active_profile_name
                self.account_list_container.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(
                                ft.Icons.RADIO_BUTTON_CHECKED if is_active else ft.Icons.RADIO_BUTTON_UNCHECKED,
                                color=ft.Colors.GREEN if is_active else ft.Colors.GREY,
                                size=20,
                            ),
                            ft.Column([
                                ft.Text(name, size=14, weight=ft.FontWeight.BOLD if is_active else None),
                                ft.Text(f"帳號: {profile.get('username', '')}", size=11, color=ft.Colors.GREY),
                            ], spacing=2, expand=True),
                            ft.IconButton(
                                ft.Icons.EDIT,
                                icon_size=18,
                                tooltip="編輯",
                                on_click=lambda e, n=name: self._edit_account(n),
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE,
                                icon_size=18,
                                icon_color=ft.Colors.RED_400,
                                tooltip="刪除",
                                on_click=lambda e, n=name: self._delete_account(n),
                            ),
                        ], alignment=ft.MainAxisAlignment.START),
                        padding=ft.padding.symmetric(horizontal=10, vertical=8),
                        border_radius=8,
                        bgcolor=ft.Colors.GREEN_900 if is_active else ft.Colors.GREY_800,
                        border=ft.border.all(1, ft.Colors.GREEN if is_active else ft.Colors.GREY_700),
                    )
                )
        
        try:
            self.page.update()
        except:
            pass
    
    def _edit_account(self, profile_name):
        """Load account into edit fields."""
        self._fill_profile_fields(profile_name)
        self.page.update()
        self.page.open(ft.SnackBar(ft.Text(f"正在編輯: {profile_name}")))
    
    def _delete_account(self, profile_name):
        """Delete an account with confirmation."""
        def confirm_delete(e):
            self.page.close(dlg)
            if profile_name in self.profiles:
                del self.profiles[profile_name]
                if self.active_profile_name == profile_name:
                    self.active_profile_name = None
                    self.config["username"] = ""
                    self.config["password"] = ""
                self._save_config_file()
                self._refresh_account_list()
                self._update_header_selectors()
                self.page.open(ft.SnackBar(ft.Text(f"✅ 已刪除: {profile_name}")))
        
        def cancel(e):
            self.page.close(dlg)
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("確認刪除"),
            content=ft.Text(f"確定要刪除帳號「{profile_name}」嗎？此操作無法復原。"),
            actions=[
                ft.TextButton("取消", on_click=cancel),
                ft.ElevatedButton("刪除", on_click=confirm_delete, 
                                 style=ft.ButtonStyle(bgcolor=ft.Colors.RED, color=ft.Colors.WHITE)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)
    

    
    def _copy_service_email(self, e):
        """Copy Service Account email to clipboard."""
        email = get_service_account_email()
        if email:
            self.page.set_clipboard(email)
            self.page.open(ft.SnackBar(ft.Text(f"✅ 已複製: {email}")))
        else:
            self.page.open(ft.SnackBar(ft.Text("⚠️ 尚未設定 credentials.json")))
    
    def _detect_worksheets(self, e):
        """Detect worksheets from the spreadsheet URL."""
        url = self.sheets_url_field.value
        if not url:
            self.page.open(ft.SnackBar(ft.Text("⚠️ 請輸入試算表網址")))
            return
        
        spreadsheet_id = extract_spreadsheet_id(url)
        if not spreadsheet_id:
            self.page.open(ft.SnackBar(ft.Text("❌ 無效的試算表網址")))
            return
        
        self.page.open(ft.SnackBar(ft.Text("🔍 正在偵測工作表...")))
        
        worksheets = list_worksheets(spreadsheet_id)
        if not worksheets:
            self.page.open(ft.SnackBar(ft.Text("❌ 無法取得工作表，請確認權限設定")))
            return
        
        # Update dropdown options
        self.sheets_worksheet_dropdown.options = [ft.dropdown.Option(ws) for ws in worksheets]
        self.sheets_worksheet_dropdown.value = worksheets[0]  # Default to first
        self.sheets_worksheet_dropdown.visible = True
        self.save_sheets_btn.visible = True
        self.page.update()
        
        self.page.open(ft.SnackBar(ft.Text(f"✅ 找到 {len(worksheets)} 個工作表")))
    
    def _save_sheets_config(self, e):
        """Save Google Sheets configuration."""
        url = self.sheets_url_field.value
        if not url:
            self.page.open(ft.SnackBar(ft.Text("⚠️ 請輸入試算表網址")))
            return
        
        spreadsheet_id = extract_spreadsheet_id(url)
        if not spreadsheet_id:
            self.page.open(ft.SnackBar(ft.Text("❌ 無效的試算表網址")))
            return
        
        sheet_name = self.sheets_worksheet_dropdown.value
        if not sheet_name:
            self.page.open(ft.SnackBar(ft.Text("⚠️ 請選擇工作表")))
            return
        
        self.config["spreadsheet_url"] = url
        self.config["spreadsheet_id"] = spreadsheet_id
        self.config["sheet_name"] = sheet_name
        
        # Fetch and save spreadsheet name
        spreadsheet_title = get_spreadsheet_name(spreadsheet_id)
        if spreadsheet_title:
            self.config["spreadsheet_title"] = spreadsheet_title
            self.log(f"📄 試算表名稱: {spreadsheet_title}")
        else:
            self.config["spreadsheet_title"] = "" # Clear if not found
            
        self._save_config_file()
        
        # Update status text and header badge
        current_title = self.config.get("spreadsheet_title", "")
        self.sheets_status_text.value = f"✅ 已綁定: {current_title} ({sheet_name})" if current_title else f"✅ 已綁定: {sheet_name}"
        self._update_sheets_badge()
        self.page.update()
        
        self.page.open(ft.SnackBar(ft.Text(f"✅ 已綁定: {sheet_name}")))
        self.log(f"📊 綁定 Google Sheets: {spreadsheet_id} / {sheet_name}")
    
    def _add_new_profile(self, e):
        """Create a new profile."""
        name = self.add_profile_name_field.value
        username = self.add_username_field.value
        password = self.add_password_field.value
        
        # Validation
        if not name or len(name) < 2:
            self.page.open(ft.SnackBar(ft.Text("⚠️ 請輸入有效的「使用者名稱」！"), bgcolor=ft.Colors.RED))
            return
        if name in self.profiles:
            self.page.open(ft.SnackBar(ft.Text("⚠️ 此使用者名稱已存在！"), bgcolor=ft.Colors.RED))
            return
        if not username or not password:
            self.page.open(ft.SnackBar(ft.Text("⚠️ 帳號或密碼不能為空！"), bgcolor=ft.Colors.RED))
            return

        # Save new profile
        self.profiles[name] = {
            "username": username,
            "password": _encode_password(password)
        }
        
        # Clear add fields
        self.add_profile_name_field.value = ""
        self.add_username_field.value = ""
        self.add_password_field.value = ""
        
        # Refresh UI
        self._refresh_account_list()
        self.page.update()
        
        self.page.open(ft.SnackBar(ft.Text(f"✅ 已新增帳號: {name}"), bgcolor=ft.Colors.GREEN))
        self._save_config_file()

    def _edit_account(self, profile_name):
        """Open edit section for a profile."""
        self.editing_profile_name = profile_name
        p = self.profiles[profile_name]
        
        # Fill edit fields
        self.edit_profile_name_field.value = profile_name
        self.edit_username_field.value = p.get("username", "")
        self.edit_password_field.value = _decode_password(p.get("password", ""))
        
        # Show edit section
        self.edit_section.visible = True
        self.page.update()

    def _save_edit_profile(self, e):
        """Save changes to the editing profile."""
        name = self.editing_profile_name
        if not name or name not in self.profiles:
            return
            
        username = self.edit_username_field.value
        password = self.edit_password_field.value
        
        if not username or not password:
            self.page.open(ft.SnackBar(ft.Text("⚠️ 帳號或密碼不能為空！"), bgcolor=ft.Colors.RED))
            return
            
        # Update profile data
        self.profiles[name]["username"] = username
        self.profiles[name]["password"] = _encode_password(password)
        
        # If this is the active profile, treat it as a live update
        if self.active_profile_name == name:
            self.config["username"] = username
            self.config["password"] = password
            self._update_header_selectors()
            
        # Hide edit section and refresh list
        self.edit_section.visible = False
        self._refresh_account_list()
        self.page.update()
        
        self.page.open(ft.SnackBar(ft.Text(f"✅ 已更新帳號: {name}"), bgcolor=ft.Colors.GREEN))
        self._save_config_file()

    def _cancel_edit(self, e):
        """Cancel editing."""
        self.edit_section.visible = False
        self.page.update()

    def _save_config_file(self):
        """Helper to save config to disk."""
        try:
            config_data = {
                "profiles": self.profiles,
                "last_profile": self.active_profile_name,
                "last_folder": self.watch_path,
                # Legacy fields (optional, can keep for safety)
                "last_username": self.config["username"],
                "last_store": self.config["store_id"],
                # Google Sheets config
                "spreadsheet_url": self.config.get("spreadsheet_url", ""),
                "spreadsheet_id": self.config.get("spreadsheet_id", ""),
                "sheet_name": self.config.get("sheet_name", ""),
                "spreadsheet_title": self.config.get("spreadsheet_title", ""),
            }
            save_config(config_data)
        except Exception as ex:
            print(f"[Config] Save error: {ex}")

    def _update_header_selectors(self, e=None):
        """Update the header bar dropdown displays."""
        try:
            # Update account display
            account_name = self.active_profile_name or "未選擇"
            self.header_account_text.value = f"👤 {account_name}"
            
            # Update store display
            store_name = self.config.get("store_id") or "不切換"
            self.header_store_text.value = f"🏪 {store_name}"
            
            self.page.update()
        except:
            pass  # Ignore if called before UI is fully built
    
    def _show_account_menu(self, e):
        """Show account selection popup menu."""
        items = []
        
        # Add existing profiles
        for name in self.profiles.keys():
            is_current = name == self.active_profile_name
            items.append(
                ft.PopupMenuItem(
                    text=f"{'✓ ' if is_current else '   '}{name}",
                    on_click=lambda e, n=name: self._select_account(n),
                )
            )
        
        if items:
            items.append(ft.PopupMenuItem())  # Divider
        
        # Add new account option
        items.append(
            ft.PopupMenuItem(
                text="➕ 新增帳號...",
                on_click=lambda e: self._go_to_settings_for_new_account(),
            )
        )
        
        # Create and show menu
        menu = ft.PopupMenuButton(
            items=items,
            data="account_menu",
        )
        
        # Use BottomSheet as alternative since PopupMenu needs different approach
        self._show_popup_at(e, items, "選擇帳號")
    
    def _show_store_menu(self, e):
        """Show store selection popup menu."""
        items = []
        current_store = self.config.get("store_id", "")
        
        for store_name in self.store_options.keys():
            is_current = store_name == current_store
            items.append(
                ft.PopupMenuItem(
                    text=f"{'✓ ' if is_current else '   '}{store_name}",
                    on_click=lambda e, s=store_name: self._select_store(s),
                )
            )
        
        self._show_popup_at(e, items, "選擇門市")
    
    def _show_popup_at(self, e, items, title):
        """Show a bottom sheet menu for selection."""
        def close_sheet(e):
            self.page.close(bs)
        
        def item_click(handler):
            def wrapper(e):
                self.page.close(bs)
                handler(e)
            return wrapper
        
        # Build menu items
        menu_items = []
        for item in items:
            if item.text:
                menu_items.append(
                    ft.ListTile(
                        title=ft.Text(item.text, size=14),
                        on_click=item_click(item.on_click) if item.on_click else None,
                    )
                )
        
        bs = ft.BottomSheet(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        ft.IconButton(ft.Icons.CLOSE, on_click=close_sheet),
                    ]),
                    ft.Divider(),
                    *menu_items,
                ], spacing=0, tight=True),
                padding=20,
            ),
        )
        self.page.open(bs)
    
    def _select_account(self, profile_name):
        """Select an account from the header menu."""
        if profile_name in self.profiles:
            self.active_profile_name = profile_name
            p = self.profiles[profile_name]
            self.config["username"] = p.get("username", "")
            self.config["password"] = _decode_password(p.get("password", ""))
            
            self._update_header_selectors()
            self._save_config_file()
            self._refresh_account_list()
            self.page.open(ft.SnackBar(ft.Text(f"✅ 已切換至: {profile_name}")))
    
    def _select_store(self, store_name):
        """Select a store from the header menu."""
        self.config["store_id"] = store_name
        self._update_header_selectors()
        self._save_config_file()
        self.page.open(ft.SnackBar(ft.Text(f"✅ 門市: {store_name}")))
    
    def _go_to_settings_for_new_account(self):
        """Navigate to settings tab to add new account."""
        self.tabs.selected_index = 1
        self.page.update()
    
    def _update_status(self, status: str, icon: str = None, color = None):
        """Update the status indicator.
        
        Args:
            status: Status text (未啟動, 監控中, 處理中, 錯誤)
            icon: Icon name (optional, auto-selected based on status)
            color: Color (optional, auto-selected based on status)
        """
        status_map = {
            "未啟動": (ft.Icons.STOP_CIRCLE, ft.Colors.GREY),
            "監控中": (ft.Icons.PLAY_CIRCLE, ft.Colors.GREEN),
            "處理中": (ft.Icons.SYNC, ft.Colors.BLUE),
            "錯誤": (ft.Icons.ERROR, ft.Colors.RED),
        }
        
        icon_name, status_color = status_map.get(status, (ft.Icons.HELP, ft.Colors.GREY))
        if icon:
            icon_name = icon
        if color:
            status_color = color
        
        self.status_icon.name = icon_name
        self.status_icon.color = status_color
        self.status_text.value = status
        self.status_text.color = status_color
        self.status_container.bgcolor = ft.Colors.with_opacity(0.15, status_color)
        self.page.update()
    
    def _update_sheets_badge(self):
        """Update the Google Sheets status badge."""
        if not hasattr(self, 'header_sheets_status'):
            return
            
        sheets_bound = bool(self.config.get("spreadsheet_id") and self.config.get("sheet_name"))
        sheet_name = self.config.get("sheet_name", "")
        spreadsheet_title = self.config.get("spreadsheet_title", "")
        
        # Display: Title (Sheet Name) if title exists, else just Sheet Name
        display_text = f"{spreadsheet_title} ({sheet_name})" if spreadsheet_title else sheet_name
        
        # Update badge content
        # Structure: Container -> Row -> [Icon, Text]
        row = self.header_sheets_status.content
        if len(row.controls) >= 2:
            # Icon
            row.controls[0].name = ft.Icons.CHECK_CIRCLE if sheets_bound else ft.Icons.WARNING
            row.controls[0].color = ft.Colors.GREEN if sheets_bound else ft.Colors.ORANGE
            # Text
            row.controls[1].value = f"📊 {display_text}" if sheets_bound else "📊 未綁定"
            row.controls[1].color = ft.Colors.GREEN if sheets_bound else ft.Colors.ORANGE
        
        # Container style
        self.header_sheets_status.bgcolor = ft.Colors.with_opacity(0.2, ft.Colors.GREEN if sheets_bound else ft.Colors.ORANGE)
        self.header_sheets_status.tooltip = f"已綁定: {display_text}" if sheets_bound else "Google Sheets 尚未綁定"
        
        self.page.update()
    
    def _check_first_time_setup(self):
        """Check if first-time setup is needed and show guide dialog."""
        has_account = bool(self.config.get("username"))
        has_store = bool(self.config.get("store_id"))
        has_sheets = bool(self.config.get("spreadsheet_id"))
        
        # If no account configured, show first-time setup dialog
        if not has_account:
            self._show_first_time_dialog()
    
    def _show_first_time_dialog(self):
        """Show first-time setup guidance dialog."""
        has_account = bool(self.config.get("username"))
        has_store = bool(self.config.get("store_id"))
        has_sheets = bool(self.config.get("spreadsheet_id"))
        
        def go_to_settings(e):
            self.page.close(dlg)
            self.tabs.selected_index = 1  # Switch to settings tab
            self.page.update()
        
        def close_dialog(e):
            self.page.close(dlg)
        
        # Build checklist
        checklist = ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE if has_account else ft.Icons.CIRCLE_OUTLINED, 
                       color=ft.Colors.GREEN if has_account else ft.Colors.GREY, size=20),
                ft.Text("新增登入帳號", 
                       color=ft.Colors.WHITE if not has_account else ft.Colors.GREY_500,
                       weight=ft.FontWeight.BOLD if not has_account else None),
                ft.Text("(必要)", size=11, color=ft.Colors.RED if not has_account else ft.Colors.GREY),
            ], spacing=10),
            ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE if has_store else ft.Icons.CIRCLE_OUTLINED, 
                       color=ft.Colors.GREEN if has_store else ft.Colors.GREY, size=20),
                ft.Text("選擇門市", 
                       color=ft.Colors.WHITE if not has_store else ft.Colors.GREY_500),
                ft.Text("(建議)", size=11, color=ft.Colors.ORANGE if not has_store else ft.Colors.GREY),
            ], spacing=10),
            ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE if has_sheets else ft.Icons.CIRCLE_OUTLINED, 
                       color=ft.Colors.GREEN if has_sheets else ft.Colors.GREY, size=20),
                ft.Text("綁定 Google 試算表", 
                       color=ft.Colors.WHITE if not has_sheets else ft.Colors.GREY_500),
                ft.Text("(選填)", size=11, color=ft.Colors.GREY),
            ], spacing=10),
        ], spacing=12)
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.ROCKET_LAUNCH, color=ft.Colors.BLUE, size=28),
                ft.Text("🎉 歡迎使用", size=20, weight=ft.FontWeight.BOLD),
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("為了開始使用自動化功能，請先完成以下設定：", size=14),
                    ft.Container(height=10),
                    checklist,
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Text("💡 完成設定後即可開始自動處理聽力報告！", size=12, color=ft.Colors.CYAN),
                        padding=10,
                        border_radius=8,
                        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.CYAN),
                    ),
                ], spacing=5),
                width=350,
            ),
            actions=[
                ft.TextButton("稍後設定", on_click=close_dialog),
                ft.ElevatedButton(
                    "前往設定",
                    icon=ft.Icons.SETTINGS,
                    on_click=go_to_settings,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)
    
    def log(self, message: str):
        """Add message to log."""
        import time
        timestamp = time.strftime("%H:%M:%S")
        self.log_list.controls.append(
            ft.Text(f"[{timestamp}] {message}", size=12)
        )
        print(f"[GUI Log] {message}")  # Debug print
        self.page.update()
    
    async def pick_folder(self, e):
        """Open folder picker dialog."""
        # Use FilePicker instead of page.get_directory_path_async
        self.file_picker.get_directory_path(dialog_title="選擇監控資料夾")
            
    def on_dialog_result(self, e: ft.FilePickerResultEvent):
        """Handle file picker result."""
        if e.path:
            self.watch_path = e.path
            self.folder_path_text.value = e.path
            self.folder_path_text.color = ft.Colors.WHITE
            self.page.update()
            self.log(f"📁 選擇資料夾: {e.path}")
            
            # Save new folder path to config
            self._save_config_file()
            
            # Auto-start monitoring as requested
            if self.monitoring:
                self.stop_monitoring()
            
            # CRITICAL: Clear old data when switching folders
            with self.processing_lock:
                self.pending_files.clear()
                self.processed_files_history.clear()
            self.detected_file = None
            self.current_file = None
            self.update_pending_list()
            self._reset_dashboard()
            self.log("🔄 已清空舊待處理清單")
                
            self.start_monitoring()
    
    def toggle_monitoring(self, e):
        """Toggle file monitoring."""
        if not self.monitoring:
            if not self.watch_path:
                self.page.open(ft.SnackBar(ft.Text("請先選擇監控資料夾")))
                return
            
            self.start_monitoring()
        else:
            self.stop_monitoring()
    
    def start_monitoring(self):
        """Start file monitoring."""
        try:
            self.monitoring = True
            self.monitor_btn.text = "⏹️ 停止監控"
            self.monitor_btn.style.bgcolor = ft.Colors.RED
            self._update_status("監控中")
            
            handler = XMLFileHandler(self._safe_on_new_file)
            self.observer = Observer()
            self.observer.schedule(handler, self.watch_path, recursive=False)
            self.observer.start()
            
            # Start polling thread as backup
            threading.Thread(target=self._polling_loop, daemon=True).start()
            
            self.log(f"🟢 開始監控: {self.watch_path}")
            
            # Initial scan
            self.page.run_task(self._initial_scan)
            self.page.update()
        except Exception as e:
            self.monitoring = False # Reset state
            self._update_status("錯誤")
            self.log(f"❌ 啟動監控失敗: {e}")
            self.page.open(ft.SnackBar(ft.Text(f"啟動失敗: {e}")))
            self.page.update()

    async def _initial_scan(self):
        """Perform initial scan for files."""
        try:
            xml_files = [
                os.path.join(self.watch_path, f) 
                for f in os.listdir(self.watch_path) 
                if f.lower().endswith('.xml')
            ]
            if xml_files:
                latest_file = max(xml_files, key=os.path.getmtime)
                self.log(f"🔎 發現既有檔案: {os.path.basename(latest_file)}")
                self._safe_on_new_file(latest_file)
        except Exception as e:
            self.log(f"⚠️ 初始掃描失敗: {e}")

    def _polling_loop(self):
        """Backup polling loop."""
        import time
        while self.monitoring:
            try:
                if self.watch_path and os.path.exists(self.watch_path):
                    files = [f for f in os.listdir(self.watch_path) if f.lower().endswith('.xml')]
                    
                    # 1. Check existing files
                    for f in files:
                        filepath = os.path.join(self.watch_path, f)
                        try:
                            # Just call the safe handler, it will deduplicate
                            if os.path.isfile(filepath):
                                self._safe_on_new_file(filepath)
                        except:
                            pass
                    
                    # 2. Cleanup history for missing files (so they can be detected if re-added)
                    with self.processing_lock:
                        # Create list of keys to safely modify dict during iteration
                        for path in list(self.processed_files_history.keys()):
                            if not os.path.exists(path):
                                del self.processed_files_history[path]
                                # print(f"[DEBUG] Cleared history for missing file: {path}")

                time.sleep(2)
            except:
                time.sleep(2)

    def _safe_on_new_file(self, filepath: str):
        """Thread-safe file handler with deduplication logic."""
        
        with self.processing_lock:
            try:
                current_mtime = os.path.getmtime(filepath)
            except OSError:
                return  # File might be gone/locked
            
            # Check if already in pending or currently being processed
            in_pending = filepath in self.pending_files
            is_current = filepath == self.current_file
            
            if in_pending or is_current:
                return
            
            # Only use mtime check to dedupe rapid duplicate events (within same detection cycle)
            if filepath in self.processed_files_history:
                last_mtime = self.processed_files_history[filepath]
                import time
                if hasattr(self, '_last_file_time') and filepath == getattr(self, '_last_filepath', None):
                    if (time.time() - self._last_file_time) < 2.0 and current_mtime == last_mtime:
                        return
            
            # Track for rapid duplicate detection
            import time
            self._last_file_time = time.time()
            self._last_filepath = filepath
            self.processed_files_history[filepath] = current_mtime
            
            # Add to pending list
            self.pending_files.append(filepath)
            self.update_pending_list()
            
            # Auto-restore window on new file
            # Auto-restore window on new file
            try:
                self.page.window.minimized = False
                self.page.window.always_on_top = True
                self.page.update()
                
                # Small delay then release always_on_top
                import time
                # time.sleep(0.1) # Cannot block here? running in thread?
                # _safe_on_new_file is called from thread, so sleep is OK but might delay main thread if using page.update?
                # Actually page.update is thread-safe in Flet.
                
                # To be safe, just keep it on top for a moment or rely on user interaction?
                # Let's toggle it off in a scheduled task if possible, but simplest is:
                self.page.window.to_front()
                self.page.window.always_on_top = False
                self.page.update()
            except:
                pass

        # Auto-process if idle
        if not self.current_file:
             self.page.run_task(self._load_file, filepath)
    
    def update_pending_list(self):
        """Update the UI list of pending files."""
        items = []
        for f in self.pending_files:
            is_selected = (f == self.detected_file)
            items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE if is_selected else ft.Icons.DESCRIPTION, 
                            size=16,
                            color=ft.Colors.GREEN if is_selected else None
                        ),
                        ft.Text(
                            os.path.basename(f), 
                            size=12, 
                            no_wrap=True, 
                            expand=True,
                            weight=ft.FontWeight.BOLD if is_selected else None,
                            color=ft.Colors.GREEN if is_selected else None,
                        ),
                        ft.Text(
                            "已選擇" if is_selected else "",
                            size=10,
                            color=ft.Colors.GREEN,
                            italic=True,
                        ) if is_selected else ft.Container(),
                    ]),
                    padding=5,
                    bgcolor=ft.Colors.GREEN_900 if is_selected else ft.Colors.GREY_800,
                    border_radius=5,
                    border=ft.border.all(2, ft.Colors.GREEN) if is_selected else None,
                    on_click=lambda e, path=f: self.select_pending_file(path),
                    ink=True,
                )
            )
        self.pending_list_view.controls = items
        self.page.update()

    def select_pending_file(self, filepath):
        """Manually select a file from queue to process."""
        # Update the selected file
        self.detected_file = filepath
        self.current_file = filepath
        
        # Refresh the pending list UI to show new selection
        self.update_pending_list()
        
        # Load the file
        self.page.run_task(self._load_file, filepath)
    
    def stop_monitoring(self):
        """Stop file monitoring."""
        self.monitoring = False
        self.monitor_btn.text = "▶️ 開始監控"
        self.monitor_btn.style.bgcolor = ft.Colors.BLUE
        self._update_status("未啟動")
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        self.log("⏹️ 監控已停止")
        self.page.update()
    
    # on_new_file is replaced by _safe_on_new_file but kept for reference if needed
    def on_new_file(self, filepath: str):
        self._safe_on_new_file(filepath)
    
    async def _load_file(self, filepath: str):
        """Load and parse XML file."""
        print(f"[DEBUG] _load_file: Start loading {filepath}")
        self.current_file = filepath 
        self.detected_file = filepath
        self.log(f"📄 載入檔案: {os.path.basename(filepath)}")
        
        try:
            sessions = parse_noah_xml(filepath)
            print(f"[DEBUG] Parse result sessions count: {len(sessions) if sessions else 0}")
            if sessions:
                self.xml_data = sessions[0]
                patient_name = self.xml_data.get("Target_Patient_Name", "未知")
                birth_date = self.xml_data.get("Patient_BirthDate", "")
                
                self.patient_name.value = f"👤 {patient_name}"
                self.patient_info.value = f"生日: {birth_date} | 檔案: {os.path.basename(filepath)}"
                self.process_btn.disabled = False
                
                # Update preview
                preview = "\n".join([f"{k}: {v}" for k, v in self.xml_data.items() 
                                    if v and k not in ["Raw_FirstName", "Raw_LastName"]])
                self.xml_preview.value = preview
                
                self.log(f"✅ 解析成功: {patient_name}")
                
                # Restore window and bring to front
                self.page.window_minimized = False
                self.page.window_always_on_top = True
                self.page.update()
                import time
                time.sleep(0.1)
                self.page.window_always_on_top = False
                self.page.update()
            else:
                self.patient_name.value = "⚠️ 無法解析檔案"
                
        except Exception as e:
            self.log(f"❌ 解析錯誤: {e}")
            self.patient_name.value = "❌ 解析錯誤"
        
        self.page.update()
    
    def open_wizard(self, e):
        """Open the session selection wizard."""
        if not self.detected_file:
            return
            
        # Validate Config
        if not self.config.get("username") or not self.config.get("password"):
            def go_to_settings(e):
                self.page.close(dlg)
                self.tabs.selected_index = 1 # Switch to Settings tab
                self.page.update()

            dlg = ft.AlertDialog(
                title=ft.Text("⚠️ 未選擇身份"),
                content=ft.Text("請先至「設定」分頁新增或選擇一個身份，才能開始作業。"),
                actions=[
                    ft.TextButton("前往設定", on_click=go_to_settings),
                    ft.TextButton("取消", on_click=lambda e: self.page.close(dlg)),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.open(dlg)
            return
        
        try:
            session_info = get_available_sessions(self.detected_file)
        except Exception as ex:
            self.page.open(ft.SnackBar(ft.Text(f"錯誤: {ex}")))
            return
        
        # Add spreadsheet_id to session_info for wizard
        session_info["spreadsheet_id"] = self.config.get("spreadsheet_id", "")
        
        # Create wizard dialog
        wizard = SessionWizard(self.page, session_info, self.on_wizard_complete)
        wizard.open()
    
    def on_wizard_complete(self, result: Dict[str, Any]):
        """Handle wizard completion."""
        if result is None:
            return
        
        self.log(f"📝 Inspector: {result['inspector_name']}")
        self.log(f"📅 PTA: {result['pta_selection']}")
        self.log(f"📅 Tymp: {result['tymp_selection']}")
        
        # Build config
        # Note: store_id in self.config is the display name, need to convert to actual ID
        store_display_name = self.config.get("store_id", "")
        store_actual_id = self.store_options.get(store_display_name, "")
        
        config = {
            "url": self.config.get("url", "https://crm.greattree.com.tw/"),
            "username": self.config.get("username", ""),
            "password": self.config.get("password", ""),
            "store_id": store_actual_id,  # Use converted ID
        }
        
        self.log(f"🏪 店別: {store_display_name} (ID: {store_actual_id})")
        
        # Build payload from XML data + wizard result
        sessions = parse_noah_xml(self.detected_file)
        selected_data = self._merge_session_data(sessions, result)
        
        # Run automation in background thread
        # Run automation in background thread
        self.log("🚀 開始處理...")
        
        # 1. Create Progress Dialog
        self.progress_text = ft.Text("正在初始化...", size=16)
        self.progress_bar = ft.ProgressBar(width=300, color=ft.Colors.BLUE)
        
        self.progress_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.ProgressRing(width=20, height=20, stroke_width=2), ft.Text(" 自動化處理中...")]),
            content=ft.Container(
                content=ft.Column([
                    self.progress_text,
                    ft.Container(height=10),
                    self.progress_bar,
                    ft.Container(height=5),
                    ft.Text("請勿關閉視窗，這可能需要幾秒鐘...", size=12, color=ft.Colors.GREY),
                ], tight=True),
                height=100,
                width=350,
            ),
            actions=[],
        )
        self.page.open(self.progress_dialog)
        self.page.update()
        
        # 2. Define Callback
        def progress_callback(msg):
            self.page.run_task(self._update_progress_ui, msg)

        threading.Thread(
            target=self._run_automation,
            args=(selected_data, self.detected_file, config, result, progress_callback)
        ).start()

    def _update_progress_ui(self, msg):
        """Update progress dialog text."""
        self.progress_text.value = str(msg)
        self.page.update()
    
    def _merge_session_data(self, sessions: List[Dict], result: Dict) -> Dict:
        """Merge selected session data with wizard results."""
        pta_date = result["pta_selection"].split()[0] if result["pta_selection"] else None
        tymp_date = result["tymp_selection"].split()[0] if result["tymp_selection"] else None
        
        selected_data = {}
        
        for session in sessions:
            full_date = session.get("FullTestDate", "").split("T")[0]
            
            if pta_date and full_date == pta_date:
                for key, value in session.items():
                    if key.startswith("PTA_") or key.startswith("Speech_") or key.startswith("Test"):
                        selected_data[key] = value
                # Also add FullTestDate for Google Sheets C column
                selected_data["FullTestDate"] = session.get("FullTestDate", "")
            
            if tymp_date and full_date == tymp_date:
                for key, value in session.items():
                    if key.startswith("Tymp_"):
                        selected_data[key] = value
        
        # Add patient info
        if sessions:
            selected_data["Target_Patient_Name"] = sessions[0].get("Target_Patient_Name", "")
            selected_data["Patient_BirthDate"] = sessions[0].get("Patient_BirthDate", "")
        
        # Add wizard results
        selected_data["InspectorName"] = result["inspector_name"]
        selected_data["Otoscopy_Left_Clean"] = result["otoscopy"]["left_clean"]
        selected_data["Otoscopy_Left_Intact"] = result["otoscopy"]["left_intact"]
        selected_data["Otoscopy_Right_Clean"] = result["otoscopy"]["right_clean"]
        selected_data["Otoscopy_Right_Intact"] = result["otoscopy"]["right_intact"]
        selected_data["Speech_Left_Type"] = "1"
        selected_data["Speech_Right_Type"] = "1"
        
        return selected_data
    
    def _parse_pta_value(self, value) -> Optional[float]:
        """Parse PTA value from string (may have NR suffix) to float."""
        if value is None:
            return None
        try:
            # Remove NR suffix if present
            str_val = str(value).replace("NR", "").strip()
            return float(str_val)
        except (ValueError, TypeError):
            return None
    
    def _run_automation(self, payload: Dict, filepath: str, config: Dict, wizard_result: Dict, progress_callback=None):
        """Run automation in background thread."""
        try:
            run_automation_sync(payload, filepath, config, headless=True, progress_callback=progress_callback)
            # Pass wizard_result and payload for sheets writing
            self.page.run_task(self._on_automation_success, filepath, wizard_result, payload)
        except Exception as e:
            self.page.run_task(self._on_automation_error, str(e), filepath)
    
    async def _on_automation_success(self, filepath: str = None, wizard_result: Dict = None, payload: Dict = None):
        """Handle automation success."""
        if hasattr(self, 'progress_dialog'):
            self.page.close(self.progress_dialog)
        self.log("✅ 上傳成功!")
        
        # Write to Google Sheets if enabled
        if wizard_result and wizard_result.get("write_to_sheets") and wizard_result.get("sheets_data"):
            self.log("📊 寫入 Google 試算表...")
            try:
                spreadsheet_id = self.config.get("spreadsheet_id")
                if not spreadsheet_id:
                    self.log("⚠️ 未設定試算表 ID")
                else:
                    # Calculate PTA from payload
                    # Note: Parser uses PTA_{Side}_Air_{Freq} format
                    right_pta = calculate_pta(
                        self._parse_pta_value(payload.get("PTA_Right_Air_500")),
                        self._parse_pta_value(payload.get("PTA_Right_Air_1000")),
                        self._parse_pta_value(payload.get("PTA_Right_Air_2000")),
                        self._parse_pta_value(payload.get("PTA_Right_Air_4000")),
                    )
                    left_pta = calculate_pta(
                        self._parse_pta_value(payload.get("PTA_Left_Air_500")),
                        self._parse_pta_value(payload.get("PTA_Left_Air_1000")),
                        self._parse_pta_value(payload.get("PTA_Left_Air_2000")),
                        self._parse_pta_value(payload.get("PTA_Left_Air_4000")),
                    )
                    
                    print(f"[DEBUG] Right PTA: {right_pta}, Left PTA: {left_pta}")
                    
                    # Get sheets data
                    sheets_data = wizard_result["sheets_data"]
                    
                    # Build row
                    row = build_row_data(
                        inspector_name=wizard_result.get("inspector_name", ""),
                        test_date=payload.get("FullTestDate", "").split("T")[0] if payload.get("FullTestDate") else "",
                        patient_name=payload.get("Target_Patient_Name", ""),
                        birth_date=payload.get("Patient_BirthDate", ""),
                        phone=sheets_data.get("phone", ""),
                        customer_source=sheets_data.get("customer_source", ""),
                        clinic_name=sheets_data.get("clinic_name", ""),
                        has_invitation_card=sheets_data.get("invitation_card", ""),
                        store_code=sheets_data.get("store_code", ""),
                        recommend_id=sheets_data.get("recommend_id", ""),
                        voucher_count=sheets_data.get("voucher_count", ""),
                        voucher_id=sheets_data.get("voucher_id", ""),
                        is_deal=sheets_data.get("is_deal", ""),
                        transaction_amount=sheets_data.get("transaction_amount", ""),
                        right_pta=right_pta,
                        left_pta=left_pta,
                    )
                    
                    # Get sheet name from config
                    sheet_name = self.config.get("sheet_name", "來客紀錄")
                    
                    success = append_row_to_sheet(spreadsheet_id, row, sheet_name)
                    if success:
                        self.log("✅ 已寫入試算表!")
                    else:
                        self.log("⚠️ 試算表寫入失敗")
            except Exception as ex:
                self.log(f"⚠️ 試算表錯誤: {ex}")
        
        # Remove from pending list upon success
        target = filepath or self.detected_file
        
        # Clear processing history - both exact path AND any path with same basename
        if target:
            with self.processing_lock:
                target_basename = os.path.basename(target)
                # Remove exact match
                if target in self.processed_files_history:
                    del self.processed_files_history[target]
                # Also remove any entries with same filename
                keys_to_remove = [
                    path for path in self.processed_files_history 
                    if os.path.basename(path) == target_basename
                ]
                for key in keys_to_remove:
                    del self.processed_files_history[key]
        
        if target and target in self.pending_files:
            self.pending_files.remove(target)
            self.update_pending_list()
            
        self.page.open(ft.SnackBar(ft.Text("✅ 處理完成!")))
        self._reset_dashboard()
    
    async def _on_automation_error(self, error: str, filepath: str = None):
        """Handle automation error."""
        if hasattr(self, 'progress_dialog'):
            self.page.close(self.progress_dialog)
        self.log(f"❌ 錯誤: {error}")
        
        # Remove from pending list (file moved to failed)
        target = filepath or self.detected_file
        
        # CRITICAL: Clear from processed history - both exact path AND any path with same basename
        # This ensures re-detection even if file is moved back with different path
        if target:
            with self.processing_lock:
                target_basename = os.path.basename(target)
                # Remove exact match
                if target in self.processed_files_history:
                    del self.processed_files_history[target]
                # Also remove any entries with same filename
                keys_to_remove = [
                    path for path in self.processed_files_history 
                    if os.path.basename(path) == target_basename
                ]
                for key in keys_to_remove:
                    del self.processed_files_history[key]
                print(f"[DEBUG] Cleared {len(keys_to_remove) + 1} entries from processed history for re-detection")
        
        if target and target in self.pending_files:
            self.pending_files.remove(target)
            self.update_pending_list()

        # Specific handling for Login Failure
        if "登入失敗" in error:
            def go_settings(e):
                self.page.close(dlg)
                self.tabs.selected_index = 2 # Jump to Settings tab
                self.page.update()
            
            dlg = ft.AlertDialog(
                title=ft.Text("❌ 登入失敗"),
                content=ft.Text(f"{error}\n\n請檢查您的帳號密碼設定是否正確。"),
                actions=[
                    ft.TextButton("前往設定修正", on_click=go_settings),
                    ft.TextButton("關閉", on_click=lambda e: self.page.close(dlg))
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.open(dlg)
        else:
            self.page.open(ft.SnackBar(ft.Text(f"❌ 錯誤: {error}")))
            
        self._reset_dashboard()
        self.page.update()
    
    def _reset_dashboard(self):
        """Reset dashboard for next file."""
        self.detected_file = None
        self.current_file = None  # CRITICAL: Reset current_file so moved-back files can be re-detected
        self.xml_data = {}
        self.patient_name.value = "等待偵測 XML 檔案..."
        self.patient_info.value = ""
        self.process_btn.disabled = True
        self.xml_preview.value = ""
        self.log("🔄 已重置,準備處理下一個檔案")
        self.page.update()


class SessionWizard:
    """Multi-page wizard dialog for session selection."""
    
    def __init__(self, page: ft.Page, session_info: Dict, on_complete):
        self.page = page
        self.session_info = session_info
        self.on_complete = on_complete
        self.current_page = 0
        
        # Data
        self.inspector_name = ft.TextField(label="檢查人員姓名 *", prefix_icon=ft.Icons.PERSON)
        
        pta_options = [s["display"] for s in session_info.get("pta_sessions", [])]
        tymp_options = [s["display"] for s in session_info.get("tymp_sessions", [])]
        
        self.pta_dropdown = ft.Dropdown(
            label="選擇純音聽力報告",
            options=[ft.dropdown.Option(o) for o in pta_options] if pta_options else [ft.dropdown.Option("無")],
            value=pta_options[0] if pta_options else "無",
        )
        
        self.tymp_dropdown = ft.Dropdown(
            label="選擇中耳鼓室圖報告",
            options=[ft.dropdown.Option(o) for o in tymp_options] if tymp_options else [ft.dropdown.Option("無")],
            value=tymp_options[0] if tymp_options else "無",
        )
        
        self.left_image_path = None
        self.right_image_path = None
        self.left_image_text = ft.Text("未選擇檔案", size=12, color=ft.Colors.GREY_400)
        self.right_image_text = ft.Text("未選擇檔案", size=12, color=ft.Colors.GREY_400)
        
        self.left_file_picker = ft.FilePicker(on_result=self.on_left_image_picked)
        self.right_file_picker = ft.FilePicker(on_result=self.on_right_image_picked)
        self.page.overlay.extend([self.left_file_picker, self.right_file_picker])

        self.left_clean = ft.RadioGroup(
            content=ft.Row([ft.Radio(value="True", label="是", fill_color=ft.Colors.WHITE), ft.Radio(value="False", label="否", fill_color=ft.Colors.WHITE)]),
            value="True",
        )
        self.left_intact = ft.RadioGroup(
            content=ft.Row([ft.Radio(value="True", label="是", fill_color=ft.Colors.WHITE), ft.Radio(value="False", label="否", fill_color=ft.Colors.WHITE)]),
            value="True",
        )
        self.right_clean = ft.RadioGroup(
            content=ft.Row([ft.Radio(value="True", label="是", fill_color=ft.Colors.WHITE), ft.Radio(value="False", label="否", fill_color=ft.Colors.WHITE)]),
            value="True",
        )
        self.right_intact = ft.RadioGroup(
            content=ft.Row([ft.Radio(value="True", label="是", fill_color=ft.Colors.WHITE), ft.Radio(value="False", label="否", fill_color=ft.Colors.WHITE)]),
            value="True",
        )
        
        # --- Google Sheets Integration Fields ---
        # Check if Google Sheets is configured
        self.sheets_configured = bool(session_info.get("spreadsheet_id"))
        
        # Checkbox to enable writing to Google Sheets
        self.sheets_checkbox = ft.Checkbox(
            label="同時寫入 Google 試算表",
            value=False,
            on_change=self._toggle_sheets_fields,
        )
        
        # Customer source options (exact 13 options from user)
        self.customer_source_options = [
            "門市轉介", "員工本人", "員工家屬", "門市DM/海報", "招牌", 
            "過路客", "自邀客", "舊客轉介", "GOOGLE", "FB/LINE", 
            "聽篩活動", "門市聽篩(蓋門市聽篩章)", "簡訊廣告"
        ]
        
        # Create checkboxes for multi-select customer source
        self.customer_source_checkboxes = {}
        for option in self.customer_source_options:
            self.customer_source_checkboxes[option] = ft.Checkbox(
                label=option, 
                value=False,
                on_change=self._update_customer_source_display,
            )
        
        # Invitation card options
        invitation_card_options = ["有", "無"]
        
        # Is Deal options (T column)
        is_deal_options = ["是", "否"]
        
        # Fields for Google Sheets
        self.sheets_phone = ft.TextField(
            label="電話",
            prefix_icon=ft.Icons.PHONE,
        )
        
        # Customer source selected display
        self.customer_source_display = ft.TextField(
            label="顧客來源 (可複選)",
            read_only=True,
            prefix_icon=ft.Icons.SOURCE,
            hint_text="點擊選擇...",
        )
        
        # Customer source popup with checkboxes
        self.customer_source_popup = ft.PopupMenuButton(
            icon=ft.Icons.ARROW_DROP_DOWN,
            items=[
                ft.PopupMenuItem(
                    content=self.customer_source_checkboxes[opt],
                ) for opt in self.customer_source_options
            ],
            tooltip="選擇顧客來源",
        )
        
        # Customer source multi-select container
        self.sheets_customer_source_container = ft.Container(
            content=ft.Row([
                ft.Container(self.customer_source_display, expand=True),
                self.customer_source_popup,
            ]),
        )
        
        self.sheets_clinic_name = ft.TextField(
            label="診所名稱 (選填)",
            prefix_icon=ft.Icons.LOCAL_HOSPITAL,
        )
        self.sheets_invitation_card = ft.Dropdown(
            label="有無邀請卡",
            options=[ft.dropdown.Option(o) for o in invitation_card_options],
            prefix_icon=ft.Icons.CARD_GIFTCARD,
            on_change=self._toggle_invitation_card_fields,
        )
        self.sheets_is_deal = ft.Dropdown(
            label="是否成交 (T欄)",
            options=[ft.dropdown.Option(o) for o in is_deal_options],
            prefix_icon=ft.Icons.HANDSHAKE,
            on_change=self._toggle_transaction_amount,
        )
        
        # Transaction Amount (U Column) - Condition on Is Deal = "是"
        self.sheets_transaction_amount = ft.TextField(
            label="成交金額 (U欄)",
            prefix_icon=ft.Icons.ATTACH_MONEY,
            visible=False,
        )
        
        # Conditional fields for invitation card (K, M, R, S)
        self.sheets_store_code = ft.TextField(
            label="門市編號 (K欄)",
            prefix_icon=ft.Icons.STORE,
        )
        self.sheets_recommend_id = ft.TextField(
            label="推薦人工號 (M欄)",
            prefix_icon=ft.Icons.BADGE,
        )
        self.sheets_voucher_count = ft.TextField(
            label="金鑽券發放張數 (R欄)",
            prefix_icon=ft.Icons.CONFIRMATION_NUMBER,
        )
        self.sheets_voucher_id = ft.TextField(
            label="金鑽券發放編號 (S欄)",
            prefix_icon=ft.Icons.NUMBERS,
        )
        
        # Container for invitation card conditional fields (hidden by default)
        self.invitation_card_fields_container = ft.Container(
            content=ft.Column([
                ft.Text("📋 邀請卡相關資料", size=12, color=ft.Colors.ORANGE),
                self.sheets_store_code,
                self.sheets_recommend_id,
                self.sheets_voucher_count,
                self.sheets_voucher_id,
            ], spacing=10),
            visible=False,
        )
        
        # Container for sheets fields (hidden by default)
        self.sheets_fields_container = ft.Container(
            content=ft.Column([
                ft.Divider(),
                ft.Text("📊 Google 試算表額外資訊", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN),
                self.sheets_phone,
                self.sheets_customer_source_container,
                self.sheets_clinic_name,
                self.sheets_invitation_card,
                self.invitation_card_fields_container,
                self.sheets_is_deal,
                self.sheets_transaction_amount,
            ], spacing=10, scroll=ft.ScrollMode.AUTO),
            visible=False,
        )
        
        self.build_dialog()

    def build_dialog(self):
        """Build the wizard dialog."""
        patient_name = self.session_info["patient_info"].get("Target_Patient_Name", "未知")
        birth_date = self.session_info["patient_info"].get("Patient_BirthDate", "")
        
        # Title with Close Button
        self.title_row = ft.Row([
            ft.Text("📋 聽力報告設定精靈", size=20, weight=ft.FontWeight.BOLD),
            ft.IconButton(ft.Icons.CLOSE, on_click=self.close, icon_color=ft.Colors.GREY, tooltip="關閉")
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        # Page 1: Basic settings
        self.page1 = ft.Column([
            ft.Text("步驟 1/3：基本設定", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"👤 病患: {patient_name}", weight=ft.FontWeight.BOLD),
                        ft.Text(f"🎂 生日: {birth_date}", color=ft.Colors.GREY),
                    ]),
                    padding=15,
                ),
            ),
            self.inspector_name,
            self.pta_dropdown,
            self.tymp_dropdown,
        ], spacing=15)
        
        # Page 2: Otoscopy
        self.page2 = ft.Column([
            ft.Text("步驟 2/3：耳鏡檢查設定", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE),
            # Left ear (Blue Theme)
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("👂 左耳 Left", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=16),
                        ft.Divider(color=ft.Colors.WHITE24),
                        ft.Row([ft.Text("耳道乾淨：", width=100, color=ft.Colors.WHITE), self.left_clean]),
                        ft.Row([ft.Text("鼓膜完整：", width=100, color=ft.Colors.WHITE), self.left_intact]),
                        ft.Divider(color=ft.Colors.WHITE24),
                        ft.Row([
                            ft.ElevatedButton("上傳左耳圖", icon=ft.Icons.UPLOAD_FILE, on_click=lambda _: self.left_file_picker.pick_files(allow_multiple=False)),
                            self.left_image_text
                        ])
                    ]),
                    padding=15,
                    bgcolor=ft.Colors.BLUE_900,
                    border_radius=10,
                ),
            ),
            # Right ear (Red Theme)
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("👂 右耳 Right", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=16),
                        ft.Divider(color=ft.Colors.WHITE24),
                        ft.Row([ft.Text("耳道乾淨：", width=100, color=ft.Colors.WHITE), self.right_clean]),
                        ft.Row([ft.Text("鼓膜完整：", width=100, color=ft.Colors.WHITE), self.right_intact]),
                        ft.Divider(color=ft.Colors.WHITE24),
                        ft.Row([
                            ft.ElevatedButton("上傳右耳圖", icon=ft.Icons.UPLOAD_FILE, on_click=lambda _: self.right_file_picker.pick_files(allow_multiple=False)),
                            self.right_image_text
                        ])
                    ]),
                    padding=15,
                    bgcolor=ft.Colors.RED_900,
                    border_radius=10,
                ),
            ),
        ], spacing=15, scroll=ft.ScrollMode.AUTO)
        
        # Page 3: Summary + Google Sheets Options
        self.summary_text = ft.Text("", size=13)
        
        # Build page 3 content
        page3_content = [
            ft.Text("步驟 3/3：確認並送出", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE),
            ft.Card(
                content=ft.Container(
                    content=self.summary_text,
                    padding=20,
                ),
            ),
        ]
        
        # Add Google Sheets options if configured
        if self.sheets_configured:
            page3_content.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            self.sheets_checkbox,
                            self.sheets_fields_container,
                        ], spacing=10),
                        padding=20,
                    ),
                    color=ft.Colors.GREY_900,
                )
            )
        
        self.page3 = ft.Column(page3_content, spacing=15, scroll=ft.ScrollMode.AUTO)
        
        # Content container (increased height for Google Sheets fields)
        self.content = ft.Container(content=self.page1, width=500, height=480)
        
        # Navigation buttons
        self.prev_btn = ft.TextButton("← 上一步", on_click=self.prev_page, visible=False)
        self.next_btn = ft.ElevatedButton("下一步 →", on_click=self.next_page)
        self.submit_btn = ft.ElevatedButton(
            "🚀 送出到 CRM", 
            on_click=self.submit,
            visible=False,
            style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE),
        )
        
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Text("📋 聽力報告設定精靈", size=20, weight=ft.FontWeight.BOLD),
                ft.IconButton(ft.Icons.CLOSE, on_click=self.close, icon_color=ft.Colors.GREY, tooltip="關閉")
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            content=self.content,
            actions=[
                self.prev_btn,
                self.next_btn,
                self.submit_btn,
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
    
    def open(self):
        """Open the dialog."""
        self.page.open(self.dialog)
    
    def close(self, e=None):
        """Close the dialog."""
        self.page.close(self.dialog)
        if self.on_complete:
            self.on_complete(None)
    
    def show_page(self, index: int):
        """Show specific page."""
        self.current_page = index
        
        # Define actions based on page
        actions = self.dialog.actions
        actions.clear()
        
        if index == 0:
            self.content.content = self.page1
            self.prev_btn.visible = False
            self.next_btn.visible = True
            
            # Use spacer to push Next button to right (SPACE_BETWEEN with 2 items: spacer, next)
            actions.append(ft.Container(width=10)) 
            actions.append(self.next_btn)
            
        elif index == 1:
            self.content.content = self.page2
            self.prev_btn.visible = True
            self.next_btn.visible = True
            
            actions.append(self.prev_btn)
            actions.append(self.next_btn)
            
        elif index == 2:
            self.update_summary()
            self.content.content = self.page3
            self.prev_btn.visible = True
            self.submit_btn.visible = True 
            
            actions.append(self.prev_btn)
            actions.append(self.submit_btn)
        
        self.page.update()
        
        print(f"[Wizard] Showing page {index}")
    
    def update_summary(self):
        """Update summary text."""
        summary = f"""病患: {self.session_info['patient_info'].get('Target_Patient_Name', '')}
檢查人員: {self.inspector_name.value}
純音聽力: {self.pta_dropdown.value}
中耳鼓室圖: {self.tymp_dropdown.value}

左耳 - 乾淨: {self.left_clean.value}, 完整: {self.left_intact.value}
右耳 - 乾淨: {self.right_clean.value}, 完整: {self.right_intact.value}"""
        self.summary_text.value = summary
    
    def prev_page(self, e):
        """Go to previous page."""
        if self.current_page > 0:
            self.show_page(self.current_page - 1)
    
    def on_left_image_picked(self, e: ft.FilePickerResultEvent):
        if e.files:
            self.left_image_path = e.files[0].path
            self.left_image_text.value = e.files[0].name
            self.left_image_text.color = ft.Colors.WHITE
            self.page.update()

    def on_right_image_picked(self, e: ft.FilePickerResultEvent):
        if e.files:
            self.right_image_path = e.files[0].path
            self.right_image_text.value = e.files[0].name
            self.right_image_text.color = ft.Colors.WHITE
            self.page.update()

    def _toggle_sheets_fields(self, e):
        """Toggle visibility of Google Sheets fields when checkbox changes."""
        self.sheets_fields_container.visible = self.sheets_checkbox.value
        self.page.update()

    def _toggle_invitation_card_fields(self, e):
        """Toggle visibility of invitation card related fields."""
        show_fields = self.sheets_invitation_card.value == "有"
        self.invitation_card_fields_container.visible = show_fields
        self.page.update()

    def _toggle_transaction_amount(self, e):
        """Toggle visibility of transaction amount field."""
        show_fields = self.sheets_is_deal.value == "是"
        self.sheets_transaction_amount.visible = show_fields
        self.page.update()

    def _get_selected_customer_sources(self) -> str:
        """Get comma-separated string of selected customer sources."""
        selected = []
        for option, checkbox in self.customer_source_checkboxes.items():
            if checkbox.value:
                selected.append(option)
        return ", ".join(selected)
    
    def _update_customer_source_display(self, e):
        """Update the customer source display field when checkboxes change."""
        self.customer_source_display.value = self._get_selected_customer_sources()
        self.page.update()

    def next_page(self, e):
        """Go to next page."""
        if self.current_page == 0:
            if not self.inspector_name.value.strip():
                self.page.open(ft.SnackBar(ft.Text("請輸入檢查人員姓名")))
                return
        
        if self.current_page < 2:
            self.show_page(self.current_page + 1)
    
    def submit(self, e):
        """Submit and close dialog."""
        result = {
            "inspector_name": self.inspector_name.value,
            "pta_selection": self.pta_dropdown.value,
            "tymp_selection": self.tymp_dropdown.value,
            "otoscopy": {
                "left_clean": self.left_clean.value,
                "left_intact": self.left_intact.value,
                "right_clean": self.right_clean.value,
                "right_intact": self.right_intact.value,
                "left_image": self.left_image_path,
                "right_image": self.right_image_path,
            },
            # Google Sheets data
            "write_to_sheets": self.sheets_checkbox.value if self.sheets_configured else False,
            "sheets_data": {
                "phone": self.sheets_phone.value or "",
                "customer_source": self._get_selected_customer_sources(),
                "clinic_name": self.sheets_clinic_name.value or "",
                "invitation_card": self.sheets_invitation_card.value or "",
                "store_code": self.sheets_store_code.value or "",
                "recommend_id": self.sheets_recommend_id.value or "",
                "voucher_count": self.sheets_voucher_count.value or "",
                "voucher_id": self.sheets_voucher_id.value or "",
                "is_deal": self.sheets_is_deal.value or "",
                "transaction_amount": self.sheets_transaction_amount.value or "",
            } if self.sheets_checkbox.value and self.sheets_configured else None,
        }
        self.close()
        self.on_complete(result)


def main(page: ft.Page):
    """Main entry point."""
    HearingApp(page)


if __name__ == "__main__":
    ft.app(target=main)
