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
        # Status bar
        self.status_chip = ft.Chip(
            label=ft.Text("未啟動"),
            leading=ft.Icon(ft.Icons.STOP_CIRCLE, color=ft.Colors.GREY),
            bgcolor=ft.Colors.GREY_900,
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
        
        # User info display (account + store)
        self.user_info_account = ft.Text("帳號: 10158", size=12, color=ft.Colors.GREY_400)
        self.user_info_store = ft.Text("店別: 不切換 (使用預設)", size=12, color=ft.Colors.GREY_400)
        
        # Main layout
        self.page.add(
            ft.Container(
                content=ft.Column([
                    # Top bar
                    ft.Container(
                        content=ft.Row([
                            ft.Text("🏥 大樹聽中行政自動化", size=20, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            self.status_chip,
                        ]),
                        padding=ft.padding.symmetric(horizontal=20, vertical=10),
                        bgcolor=ft.Colors.GREY_900,
                    ),
                    # User info bar (under title, before tabs)
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.PERSON, size=14, color=ft.Colors.GREY_500),
                            self.user_info_account,
                            ft.Container(width=20),
                            ft.Icon(ft.Icons.STORE, size=14, color=ft.Colors.GREY_500),
                            self.user_info_store,
                        ], spacing=5),
                        padding=ft.padding.symmetric(horizontal=20, vertical=5),
                        bgcolor=ft.Colors.GREY_800,
                    ),
                    # Tabs
                    self.tabs,
                ]),
                expand=True,
            )
        )
        
        # Sync header with loaded config
        self._update_user_info_bar()
    
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
        
        # --- Section 0: Global Settings (Store) ---
        self.store_dropdown = ft.Dropdown(
            label="操作店別",
            options=[ft.dropdown.Option(key=k, text=k) for k in self.store_options.keys()],
            # Initialize with loaded config store_id
            value=self.config.get("store_id") if self.config.get("store_id") else "不切換 (使用預設)",
            on_change=self._save_global_store, # New handler
            prefix_icon=ft.Icons.STORE,
            text_size=16,
        )

        # --- Section 1: Profile Selection ---
        profile_options = [ft.dropdown.Option(key=name, text=name) for name in self.profiles.keys()]
        
        dropdown_hint = "請選擇要使用的身份..."
        if not self.profiles:
            dropdown_hint = "未偵測到帳號，請先新增"

        self.profile_dropdown = ft.Dropdown(
            label="📋 選擇帳號 (切換身份)",
            hint_text=dropdown_hint,
            options=profile_options,
            value=self.active_profile_name,
            on_change=self._on_profile_select,
            prefix_icon=ft.Icons.SWITCH_ACCOUNT,
            text_size=16,
        )

        # --- Section 2: Profile Editing ---
        self.profile_name_field = ft.TextField(
            label="👤 使用者名稱 (例如: 王小明)",
            hint_text="輸入自定義名稱以供識別",
            prefix_icon=ft.Icons.BADGE,
        )
        
        self.username_field = ft.TextField(
            label="CRM 帳號 (工號)",
            prefix_icon=ft.Icons.PERSON,
        )
        
        self.password_field = ft.TextField(
            label="CRM 密碼",
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK,
        )

        self.save_profile_btn = ft.ElevatedButton(
            "💾 新增 / 更新帳號",
            icon=ft.Icons.SAVE,
            on_click=self._save_profile,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREEN,
                padding=15,
            )
        )
        
        # Initialize fields if active profile exists
        if self.active_profile_name:
            self._fill_profile_fields(self.active_profile_name)
        
        return ft.Container(
            content=ft.Column([
                # Card 0: Global Environment
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("🏢 店別選擇設定", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
                            self.store_dropdown,
                            ft.Text("💡 此設定為全域共用，切換帳號時不會改變。", size=12, color=ft.Colors.GREY),
                        ], spacing=10),
                        padding=20,
                    ),
                    color=ft.Colors.GREY_900,
                ),
                
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),

                # Card 1: Select Profile
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("👤 身分切換", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
                            self.profile_dropdown,
                            ft.Text("💡 選擇後，系統將自動使用該帳號密碼進行作業。", size=12, color=ft.Colors.GREY),
                        ], spacing=10),
                        padding=20,
                    ),
                    color=ft.Colors.GREY_900,
                ),
                
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                
                # Card 2: Edit/Create Profile
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.EDIT_SQUARE, color=ft.Colors.ORANGE),
                                ft.Text("新增 / 編輯帳號資料", size=18, weight=ft.FontWeight.BOLD),
                            ]),
                            ft.Divider(),
                            self.profile_name_field,
                            self.username_field,
                            self.password_field,
                            # Store and URL removed from here
                            ft.Container(height=10),
                            self.save_profile_btn,
                        ], spacing=15),
                        padding=30,
                    ),
                ),
            ], scroll=ft.ScrollMode.AUTO),
            padding=20,
            expand=True,
        )
    
    def _fill_profile_fields(self, profile_name):
        """Fill editing fields with profile data."""
        if profile_name in self.profiles:
            p = self.profiles[profile_name]
            self.profile_name_field.value = profile_name
            self.username_field.value = p.get("username", "")
            self.password_field.value = _decode_password(p.get("password", ""))
            # Store ID is no longer per-profile
    
    def _save_global_store(self, e):
        """Save the global store setting."""
        store = self.store_dropdown.value
        self.config["store_id"] = store
        self._update_user_info_bar()
        self._save_config_file()
    
    def _on_profile_select(self, e):
        """Handle profile selection."""
        name = self.profile_dropdown.value
        if name and name in self.profiles:
            self.active_profile_name = name
            
            # 1. Fill fields
            self._fill_profile_fields(name)
            self.page.update()
            
            # 2. Update Active Config
            p = self.profiles[name]
            self.config["username"] = p.get("username", "")
            self.config["password"] = _decode_password(p.get("password", ""))
            # Do NOT update store_id from profile
            
            # 3. Update Header
            self._update_user_info_bar()
            
            # 4. Save "Last Active" choice
            self._save_config_file()


    def _save_profile(self, e):
        """Save or create a profile."""
        name = self.profile_name_field.value
        username = self.username_field.value
        password = self.password_field.value
        # Store is global, not part of profile saving
        
        # Validation
        if not name or len(name) < 2:
            self.page.open(ft.SnackBar(ft.Text("⚠️ 請輸入有效的「使用者名稱」！"), bgcolor=ft.Colors.RED))
            return
        if not username or not password:
            self.page.open(ft.SnackBar(ft.Text("⚠️ 帳號或密碼不能為空！"), bgcolor=ft.Colors.RED))
            return

        # Save to profiles
        self.profiles[name] = {
            "username": username,
            "password": _encode_password(password)
            # No store_id
        }
        
        # Update dropdown options
        self.profile_dropdown.options = [ft.dropdown.Option(key=n, text=n) for n in self.profiles.keys()]
        self.profile_dropdown.value = name
        self.active_profile_name = name
        
        # Update active config immediately
        self.config["username"] = username
        self.config["password"] = password
        # Store is independent
        
        self.page.update()
        self._update_user_info_bar()
        self.page.open(ft.SnackBar(ft.Text(f"✅ 已儲存個人檔案: {name}"), bgcolor=ft.Colors.GREEN))
        
        # Persist to file
        self._save_config_file()
        
        self.page.update()
        self._update_user_info_bar()
        self.page.open(ft.SnackBar(ft.Text(f"✅ 已儲存個人檔案: {name}"), bgcolor=ft.Colors.GREEN))
        
        # Persist to file
        self._save_config_file()

    def _save_config_file(self):
        """Helper to save config to disk."""
        try:
            config_data = {
                "profiles": self.profiles,
                "last_profile": self.active_profile_name,
                "last_folder": self.watch_path,
                # Legacy fields (optional, can keep for safety)
                "last_username": self.config["username"],
                "last_store": self.config["store_id"]
            }
            save_config(config_data)
        except Exception as ex:
            print(f"[Config] Save error: {ex}")

    def _update_user_info_bar(self, e=None):
        """Update the user info bar with current settings."""
        try:
            self.user_info_account.value = f"帳號: {self.username_field.value}"
            self.user_info_store.value = f"店別: {self.store_dropdown.value}"
            self.page.update()
        except:
            pass  # Ignore if called before UI is fully built
    
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
            self.status_chip.label.value = "監控中..."
            self.status_chip.leading.name = ft.Icons.RADIO_BUTTON_CHECKED
            self.status_chip.leading.color = ft.Colors.GREEN
            
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
        self.status_chip.label.value = "已停止"
        self.status_chip.leading.name = ft.Icons.STOP_CIRCLE
        self.status_chip.leading.color = ft.Colors.GREY
        
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
        self.log("🚀 開始處理...")
        threading.Thread(
            target=self._run_automation,
            args=(selected_data, self.detected_file, config, result)
        ).start()
    
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
    
    def _run_automation(self, payload: Dict, filepath: str, config: Dict, wizard_result: Dict):
        """Run automation in background thread."""
        try:
            run_automation_sync(payload, filepath, config, headless=False)
            self.page.run_task(self._on_automation_success, filepath)
        except Exception as e:
            self.page.run_task(self._on_automation_error, str(e), filepath)
    
    async def _on_automation_success(self, filepath: str = None):
        """Handle automation success."""
        self.log("✅ 上傳成功!")
        
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
        
        # Page 3: Summary
        self.summary_text = ft.Text("", size=13)
        self.page3 = ft.Column([
            ft.Text("步驟 3/3：確認並送出", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE),
            ft.Card(
                content=ft.Container(
                    content=self.summary_text,
                    padding=20,
                ),
            ),
        ], spacing=15)
        
        # Content container
        self.content = ft.Container(content=self.page1, width=500, height=400)
        
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
            }
        }
        self.close()
        self.on_complete(result)


def main(page: ft.Page):
    """Main entry point."""
    HearingApp(page)


if __name__ == "__main__":
    ft.app(target=main)
