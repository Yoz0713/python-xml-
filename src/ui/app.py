import flet as ft
from watchdog.observers import Observer
import threading
import os

from src.ui.theme import AppTheme
from src.ui.components.app_navigation import AppNavigation
from src.ui.components.session_wizard import SessionWizard
from src.ui.pages.dashboard import DashboardPage
from src.ui.pages.settings import SettingsPage
from src.config_handler import load_config, save_config, encode_password, decode_password
from src.file_watcher import XMLFileHandler
from src.parser import parse_noah_xml, get_available_sessions

# Store options (店家選擇)
STORE_OPTIONS = {
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

class HearingApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "大樹聽中行政自動化 Pro"
        self.page.theme = AppTheme.get_theme()
        self.page.padding = 0
        self.page.window.width = 1200
        self.page.window.height = 800
        self.page.bgcolor = AppTheme.BACKGROUND
        
        # --- State ---
        self.config = load_config()
        self.profiles = self.config.get("profiles", {})
        self.watch_path = self.config.get("last_folder", "")
        self.active_profile_name = self.config.get("last_profile", "")
        self.store_id = self.config.get("store_id", "")
        
        # Store options reference
        self.store_options = STORE_OPTIONS
        
        # Monitoring State
        self.monitoring = False
        self.observer = None
        
        # Selected file for processing
        self.selected_file = None
        self.xml_data = {}
        
        # --- UI Initialization ---
        self.dashboard_page = DashboardPage(self)
        self.settings_page = SettingsPage(self)
        
        self.pages = [
            self.dashboard_page,
            self.settings_page
        ]
        
        self.navigation = AppNavigation(self.on_nav_change)
        
        self.content_area = ft.Container(
            content=self.dashboard_page,
            expand=True,
            padding=0,
        )
        
        # Layout
        self.layout = ft.Row(
            [
                self.navigation,
                ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
                self.content_area
            ],
            expand=True,
            spacing=0,
        )
        
        self.page.add(self.layout)
        
        # Restore State
        if self.active_profile_name:
            # Logic to restore credentials if needed
            self.settings_page.refresh_profiles()
            
        self.check_sheet_status()
        self.update_dashboard_folder()

    def on_nav_change(self, e):
        idx = e.control.selected_index
        self.content_area.content = self.pages[idx]
        self.content_area.update()

    def show_snack(self, message):
        self.page.open(ft.SnackBar(ft.Text(message)))

    # --- Actions ---

    # --- Actions ---

    def pick_folder(self):
        file_picker = ft.FilePicker(on_result=self.on_folder_picked)
        self.page.overlay.append(file_picker)
        self.page.update()
        file_picker.get_directory_path()

    def on_folder_picked(self, e: ft.FilePickerResultEvent):
        if e.path:
            self.watch_path = e.path
            self.config["last_folder"] = e.path
            save_config(self.config)
            self.update_dashboard_folder()
            self.show_snack(f"已選擇資料夾: {e.path}")
            
    def update_dashboard_folder(self):
        self.dashboard_page.update_folder(self.watch_path)

    def toggle_monitoring(self):
        if not self.watch_path:
            self.show_snack("請先選擇監控資料夾")
            return
            
        if self.monitoring:
            # Stop
            if self.observer:
                self.observer.stop()
                self.observer.join()
            self.monitoring = False
            self.dashboard_page.log("停止監控", "warning")
            # Clear queue when stopping
            self.dashboard_page.clear_queue()
        else:
            # Start
            self.monitoring = True
            
            # Clear old queue first
            self.dashboard_page.clear_queue()
            
            # Scan existing XML files in folder
            self._scan_existing_files()
            
            # Start watching for new files
            event_handler = XMLFileHandler(self.on_file_detected, self.on_file_deleted)
            self.observer = Observer()
            self.observer.schedule(event_handler, self.watch_path, recursive=False)
            self.observer.start()
            self.dashboard_page.log(f"開始監控: {self.watch_path}", "success")
            
        self.dashboard_page.update_status(self.monitoring)
    
    def _scan_existing_files(self):
        """Scan the watch folder for existing XML files."""
        if not self.watch_path or not os.path.isdir(self.watch_path):
            return
        
        count = 0
        for filename in os.listdir(self.watch_path):
            if filename.lower().endswith('.xml'):
                file_path = os.path.join(self.watch_path, filename)
                self.dashboard_page.add_file_to_queue(file_path)
                count += 1
        
        if count > 0:
            self.dashboard_page.log(f"發現 {count} 個現有 XML 檔案", "info")

    def on_file_detected(self, file_path):
        """Called when a new file is detected."""
        print(f"File detected: {file_path}")
        
        filename = os.path.basename(file_path)
        self.dashboard_page.log(f"偵測到檔案: {filename}", "info")
        self.dashboard_page.add_file_to_queue(file_path)
    
    def on_file_deleted(self, file_path):
        """Called when a file is deleted."""
        print(f"File deleted: {file_path}")
        
        filename = os.path.basename(file_path)
        self.dashboard_page.log(f"檔案已刪除: {filename}", "warning")
        self.dashboard_page.remove_file_from_queue(file_path)
    
    def on_file_selected(self, file_path):
        """Called when user selects a file from the queue."""
        # Parse the XML file and update patient info
        try:
            from src.parser import parse_noah_xml
            sessions = parse_noah_xml(file_path)
            if sessions:
                xml_data = sessions[0]
                patient_name = xml_data.get("Target_Patient_Name", "未知")
                birth_date = xml_data.get("Patient_BirthDate", "")
                filename = os.path.basename(file_path)
                
                self.dashboard_page.update_patient_info(
                    f"👤 {patient_name}",
                    f"生日: {birth_date} | 檔案: {filename}"
                )
                self.dashboard_page.log(f"已選擇: {patient_name}", "success")
            else:
                self.dashboard_page.update_patient_info("⚠️ 無法解析檔案", "")
        except Exception as e:
            self.dashboard_page.log(f"解析錯誤: {e}", "error")
            self.dashboard_page.update_patient_info("❌ 解析錯誤", str(e))
    
    def open_wizard(self, file_path):
        """Open the upload wizard for the selected file."""
        if not file_path:
            return
        
        # Check if profile is selected
        if not self.active_profile_name:
            self.show_snack("請先在設定中選擇一個帳號")
            return
        
        self.selected_file = file_path
        
        try:
            session_info = get_available_sessions(file_path)
            # Add spreadsheet_id for wizard
            session_info["spreadsheet_id"] = self.config.get("spreadsheet_id", "")
            
            # Create and open wizard
            wizard = SessionWizard(self.page, session_info, self.on_wizard_complete)
            wizard.open()
            self.dashboard_page.log(f"開啟上傳精靈: {os.path.basename(file_path)}", "info")
        except Exception as e:
            self.show_snack(f"錯誤: {e}")
            self.dashboard_page.log(f"開啟精靈失敗: {e}", "error")
    
    def on_wizard_complete(self, result):
        """Handle wizard completion."""
        if result is None:
            # Wizard cancelled
            return
        
        self.wizard_result = result
        
        self.dashboard_page.log(f"檢查人員: {result['inspector_name']}", "info")
        self.dashboard_page.log(f"PTA: {result['pta_selection']}", "info")
        self.dashboard_page.log(f"Tymp: {result['tymp_selection']}", "info")
        
        # Build config for automation
        store_display_name = self.store_id
        store_actual_id = self.store_options.get(store_display_name, "")
        
        config = {
            "url": "https://crm.greattree.com.tw/",
            "username": self.profiles.get(self.active_profile_name, {}).get("username", ""),
            "password": decode_password(self.profiles.get(self.active_profile_name, {}).get("password", "")),
            "store_id": store_actual_id,
        }
        
        self.dashboard_page.log(f"店別: {store_display_name} (ID: {store_actual_id})", "info")
        
        # Build payload from XML data + wizard result
        sessions = parse_noah_xml(self.selected_file)
        selected_data = self._merge_session_data(sessions, result)
        
        self.dashboard_page.log("🚀 開始處理...", "info")
        
        # Create Progress Dialog with ProgressBar
        self.progress_text = ft.Text("正在初始化...", size=14, color=ft.Colors.GREY_700)
        self.progress_bar = ft.ProgressBar(width=300, color=ft.Colors.BLUE)
        
        # Header with gradient-like effect
        header = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.ROCKET_LAUNCH, size=24, color=ft.Colors.WHITE),
                    padding=8,
                    bgcolor=ft.Colors.BLUE_600,
                    border_radius=8,
                ),
                ft.Column([
                    ft.Text("正在處理您的報告", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_900),
                    ft.Text("系統正在自動為您填寫 CRM 資料", size=12, color=ft.Colors.GREY_600),
                ], spacing=2, expand=True),
            ], spacing=15),
            padding=ft.padding.only(bottom=20),
        )
        
        content_container = ft.Container(
            content=ft.Column([
                self.progress_text,
                ft.Container(height=10),
                self.progress_bar,
                ft.Container(height=10),
                ft.Text("請勿關閉視窗，這可能需要幾秒鐘...", size=12, color=ft.Colors.GREY_500),
            ], tight=True),
            padding=ft.padding.symmetric(horizontal=10),
        )
        
        self.progress_dialog = ft.AlertDialog(
            modal=True,
            title=None,
            content=ft.Container(
                content=ft.Column([
                    header,
                    content_container,
                ], spacing=0, tight=True),
                width=400,
                padding=20,
            ),
            actions=[],
            shape=ft.RoundedRectangleBorder(radius=16),
        )
        self.page.open(self.progress_dialog)
        self.page.update()
        
        # Define progress callback with step list
        def progress_callback(msg):
            self.page.run_task(self._update_progress_ui, msg)
        
        # Run automation in background thread
        threading.Thread(
            target=self._run_automation,
            args=(selected_data, self.selected_file, config, result, progress_callback)
        ).start()
    
    def _translate_progress_message(self, msg: str) -> str:
        """Translate technical progress messages to user-friendly Chinese."""
        translations = {
            # Browser setup
            "Starting browser...": "啟動瀏覽器",
            "Browser started successfully": "瀏覽器就緒",
            "Browser closed": "瀏覽器已關閉",
            
            # Login
            "🔐 正在登入 CRM...": "登入 CRM 系統",
            
            # Patient search
            "🔎 正在搜尋病患": "搜尋客戶資料",
            "[Search]": "搜尋中",
            
            # Form filling
            "📝 正在填寫聽力報告...": "填寫聽力評估表單",
            "[Form] Form fill complete": "表單填寫完成",
            "[Form] Filling": "填寫欄位中",
            
            # Submit
            "🚀 正在提交表單...": "提交報告至 CRM",
            "[Submit] Form submitted!": "報告已送出",
            
            # Navigation
            "[Navigate]": "導航至報告頁面",
            
            # Completion
            "✅ 自動化作業完成!": "處理完成",
        }
        
        # Check for exact matches first
        if msg in translations:
            return translations[msg]
        
        # Check for partial matches
        for key, value in translations.items():
            if key in msg:
                # For patient-specific messages, include the patient name
                if "正在搜尋病患" in msg:
                    patient_name = msg.split(":")[-1].strip().replace("...", "")
                    return f"搜尋 {patient_name}"
                return value
        
        # For form field fills, make them friendlier
        if "[Form] Filled" in msg:
            return None  # Skip individual field fills
        if "[Form] Clicked Radio" in msg:
            return None  # Skip radio clicks
        if "[Form] Uploaded file" in msg:
            return "上傳耳鏡圖片"
            
        # If no translation, return cleaned version or None for technical logs
        if msg.startswith("["):
            return None  # Skip technical debug messages
        
        return msg
    
    def _update_progress_ui(self, msg):
        """Update progress dialog text."""
        # Translate message
        friendly_msg = self._translate_progress_message(str(msg))
        
        if friendly_msg:
            self.progress_text.value = friendly_msg
            self.page.update()
    
    def _merge_session_data(self, sessions, result):
        """Merge selected session data with wizard results."""
        pta_date = result["pta_selection"].split()[0] if result["pta_selection"] and result["pta_selection"] != "無" else None
        tymp_date = result["tymp_selection"].split()[0] if result["tymp_selection"] and result["tymp_selection"] != "無" else None
        
        selected_data = {}
        
        for session in sessions:
            full_date = session.get("FullTestDate", "").split("T")[0]
            
            if pta_date and full_date == pta_date:
                for key, value in session.items():
                    if key.startswith("PTA_") or key.startswith("Speech_") or key.startswith("Test"):
                        selected_data[key] = value
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
    
    def _parse_pta_value(self, value):
        """Parse PTA value from string (may have NR suffix) to float."""
        if value is None:
            return None
        try:
            str_val = str(value).replace("NR", "").strip()
            return float(str_val)
        except (ValueError, TypeError):
            return None
    
    def _run_automation(self, payload, filepath, config, wizard_result, progress_callback=None):
        """Run automation in background thread."""
        try:
            from src.automation import run_automation_sync
            run_automation_sync(payload, filepath, config, headless=True, progress_callback=progress_callback)
            self.page.run_task(self._on_automation_success, filepath, wizard_result, payload)
        except Exception as e:
            self.page.run_task(self._on_automation_error, str(e), filepath)
    
    async def _on_automation_success(self, filepath=None, wizard_result=None, payload=None):
        """Handle automation success."""
        if hasattr(self, 'progress_dialog'):
            self.page.close(self.progress_dialog)
        self.dashboard_page.log("✅ 上傳成功!", "success")
        
        # Write to Google Sheets if enabled
        if wizard_result and wizard_result.get("write_to_sheets") and wizard_result.get("sheets_data"):
            self.dashboard_page.log("📊 寫入 Google 試算表...", "info")
            try:
                from src.sheets_writer import append_row_to_sheet, build_row_data, calculate_pta
                
                spreadsheet_id = self.config.get("spreadsheet_id")
                if not spreadsheet_id:
                    self.dashboard_page.log("⚠️ 未設定試算表 ID", "warning")
                else:
                    # Calculate PTA
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
                    
                    sheets_data = wizard_result["sheets_data"]
                    
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
                    
                    sheet_name = self.config.get("sheet_name", "來客紀錄")
                    success = append_row_to_sheet(spreadsheet_id, row, sheet_name)
                    if success:
                        self.dashboard_page.log("✅ 已寫入試算表!", "success")
                    else:
                        self.dashboard_page.log("⚠️ 試算表寫入失敗", "warning")
            except Exception as ex:
                self.dashboard_page.log(f"⚠️ 試算表錯誤: {ex}", "error")
        
        # Remove from pending list
        target = filepath or self.selected_file
        if target:
            self.dashboard_page.mark_file_processed(target)
        
        self.show_snack("✅ 處理完成!")
        self._reset_dashboard()
    
    async def _on_automation_error(self, error, filepath=None):
        """Handle automation error."""
        if hasattr(self, 'progress_dialog'):
            self.page.close(self.progress_dialog)
        self.dashboard_page.log(f"❌ 錯誤: {error}", "error")
        
        # Remove from pending list
        target = filepath or self.selected_file
        if target:
            self.dashboard_page.remove_file_from_queue(target)
        
        # Show error dialog for login failure
        if "登入失敗" in error:
            def go_settings(e):
                self.page.close(dlg)
                # Switch to settings tab
                self.content_area.content = self.settings_page
                self.content_area.update()
            
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
            self.show_snack(f"❌ 錯誤: {error}")
        
        self._reset_dashboard()
    
    def _reset_dashboard(self):
        """Reset dashboard for next file."""
        self.selected_file = None
        self.xml_data = {}
        self.dashboard_page.log("🔄 已重置，準備處理下一個檔案", "info")

    # --- Profile Management ---

    def add_profile(self, name, username, password):
        self.profiles[name] = {
            "username": username,
            "password": encode_password(password)
        }
        self.config["profiles"] = self.profiles
        save_config(self.config)
        
    def delete_profile(self, name):
        if name in self.profiles:
            del self.profiles[name]
            if self.active_profile_name == name:
                self.active_profile_name = ""
                self.config["last_profile"] = ""
            self.config["profiles"] = self.profiles
            save_config(self.config)

    def set_active_profile(self, name):
        if name in self.profiles:
            self.active_profile_name = name
            self.config["last_profile"] = name
            save_config(self.config)
    
    def set_store(self, store_name):
        """Set the current store."""
        self.store_id = store_name
        self.config["store_id"] = store_name
        save_config(self.config)

    # --- Sheets ---
    
    def update_sheet_config(self, url, sheet_id, sheet_name, title):
        self.config["spreadsheet_url"] = url
        self.config["spreadsheet_id"] = sheet_id
        self.config["sheet_name"] = sheet_name
        self.config["spreadsheet_title"] = title
        save_config(self.config)
        self.check_sheet_status()
        
    def check_sheet_status(self):
        connected = bool(self.config.get("spreadsheet_id") and self.config.get("sheet_name"))
        name = self.config.get("spreadsheet_title", "")
        self.dashboard_page.set_sheet_status(connected, name)

def main(page: ft.Page):
    HearingApp(page)

