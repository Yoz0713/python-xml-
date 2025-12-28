"""
大樹聽中行政自動化 - Flet GUI
Modern Material Design 3 interface for hearing assessment automation.
"""
import flet as ft
import asyncio
import os
import threading
from typing import Optional, Dict, Any, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.parser import parse_noah_xml, get_available_sessions
from src.automation import HearingAutomation, run_automation_sync
from src.config import FIELD_MAP


class XMLFileHandler(FileSystemEventHandler):
    """Watch for new XML files."""
    
    def __init__(self, callback):
        self.callback = callback
    
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.xml'):
            self.callback(event.src_path)


class HearingApp:
    """Main Flet Application."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.setup_page()
        
        # State
        self.detected_file: Optional[str] = None
        self.xml_data: Dict[str, Any] = {}
        self.monitoring = False
        self.observer: Optional[Observer] = None
        self.watch_path: Optional[str] = None
        
        # Config
        self.config = {
            "url": "https://crm.greattree.com.tw/",
            "username": "",
            "password": "",
            "store_id": ""
        }
        
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
                ft.Tab(text="📁 批次上傳", content=self.build_batch_tab()),
                ft.Tab(text="⚙️ 設定", content=self.build_settings_tab()),
            ],
            expand=True,
        )
        
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
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    ),
                    # Tabs
                    self.tabs,
                ]),
                expand=True,
            )
        )
    
    def build_monitor_tab(self) -> ft.Container:
        """Build the real-time monitor tab."""
        # Folder selector
        self.folder_path_text = ft.Text("選擇監控資料夾...", size=13, color=ft.Colors.GREY)
        
        self.monitor_btn = ft.ElevatedButton(
            "▶️ 開始監控",
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
            "⚙️ 設定並上傳",
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
        
        return ft.Container(
            content=ft.Column([
                # Control bar
                ft.Card(
                    content=ft.Container(
                        content=ft.Row([
                            ft.IconButton(
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=self.pick_folder,
                                tooltip="選擇資料夾",
                            ),
                            self.folder_path_text,
                            ft.Container(expand=True),
                            self.monitor_btn,
                        ]),
                        padding=10,
                    ),
                ),
                # Patient card
                patient_card,
                # Content area
                ft.Row([
                    # Left - Preview
                    ft.Container(
                        content=ft.Column([
                            ft.Text("📊 XML 資料預覽", weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=self.xml_preview,
                                bgcolor=ft.Colors.SURFACE_CONTAINER,
                                border_radius=10,
                                padding=15,
                                expand=True,
                            ),
                        ]),
                        expand=True,
                        padding=10,
                    ),
                    # Right - Log
                    ft.Container(
                        content=ft.Column([
                            ft.Text("📋 執行狀態", weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=self.log_list,
                                bgcolor=ft.Colors.SURFACE_CONTAINER,
                                border_radius=10,
                                padding=15,
                                expand=True,
                            ),
                        ]),
                        expand=True,
                        padding=10,
                    ),
                ], expand=True),
            ]),
            padding=20,
            expand=True,
        )
    
    def build_batch_tab(self) -> ft.Container:
        """Build the batch upload tab."""
        return ft.Container(
            content=ft.Column([
                ft.Text("批次上傳功能", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("選擇包含多個 XML 檔案的資料夾進行批次處理", color=ft.Colors.GREY),
                ft.ElevatedButton("選擇資料夾", icon=ft.Icons.FOLDER_OPEN),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=40,
            expand=True,
            alignment=ft.alignment.center,
        )
    
    def build_settings_tab(self) -> ft.Container:
        """Build the settings tab."""
        self.url_field = ft.TextField(
            label="CRM 網址",
            value="https://crm.greattree.com.tw/",
            prefix_icon=ft.Icons.LINK,
        )
        
        self.username_field = ft.TextField(
            label="帳號 (工號)",
            prefix_icon=ft.Icons.PERSON,
        )
        
        self.password_field = ft.TextField(
            label="密碼",
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK,
        )
        
        self.store_dropdown = ft.Dropdown(
            label="操作店別",
            options=[ft.dropdown.Option(key=k, text=k) for k in self.store_options.keys()],
            value="不切換 (使用預設)",
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("🔐 CRM 登入設定", size=18, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            self.url_field,
                            self.username_field,
                            self.password_field,
                            self.store_dropdown,
                            ft.Container(height=10),
                            ft.Text("💡 設定會在啟動自動化時使用", color=ft.Colors.GREY, size=12),
                        ], spacing=15),
                        padding=30,
                    ),
                ),
            ], scroll=ft.ScrollMode.AUTO),
            padding=40,
            expand=True,
        )
    
    def log(self, message: str):
        """Add message to log."""
        import time
        timestamp = time.strftime("%H:%M:%S")
        self.log_list.controls.append(
            ft.Text(f"[{timestamp}] {message}", size=12)
        )
        self.page.update()
    
    async def pick_folder(self, e):
        """Open folder picker dialog."""
        result = await self.page.get_directory_path_async(dialog_title="選擇監控資料夾")
        if result:
            self.watch_path = result
            self.folder_path_text.value = result
            self.page.update()
            self.log(f"📁 選擇資料夾: {result}")
    
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
        self.monitoring = True
        self.monitor_btn.content = "⏹️ 停止監控"
        self.monitor_btn.style.bgcolor = ft.Colors.RED
        self.status_chip.label.value = "監控中..."
        self.status_chip.leading.name = ft.Icons.RADIO_BUTTON_CHECKED
        self.status_chip.leading.color = ft.Colors.GREEN
        
        handler = XMLFileHandler(self.on_new_file)
        self.observer = Observer()
        self.observer.schedule(handler, self.watch_path, recursive=False)
        self.observer.start()
        
        self.log(f"🟢 開始監控: {self.watch_path}")
        self.page.update()
    
    def stop_monitoring(self):
        """Stop file monitoring."""
        self.monitoring = False
        self.monitor_btn.content = "▶️ 開始監控"
        self.monitor_btn.style.bgcolor = ft.Colors.BLUE
        self.status_chip.label.value = "已停止"
        self.status_chip.leading.name = ft.Icons.STOP_CIRCLE
        self.status_chip.leading.color = ft.Colors.GREY
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        self.log("⏹️ 監控已停止")
        self.page.update()
    
    def on_new_file(self, filepath: str):
        """Handle new XML file detection."""
        self.page.run_task(lambda: self._load_file(filepath))
    
    async def _load_file(self, filepath: str):
        """Load and parse XML file."""
        self.detected_file = filepath
        self.log(f"📄 偵測到: {os.path.basename(filepath)}")
        
        try:
            sessions = parse_noah_xml(filepath)
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
        config = {
            "url": self.url_field.value,
            "username": self.username_field.value,
            "password": self.password_field.value,
            "store_id": self.store_options.get(self.store_dropdown.value, ""),
        }
        
        self.log(f"🏪 店別: {self.store_dropdown.value}")
        
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
            self.page.run_task(lambda: self._on_automation_success())
        except Exception as e:
            self.page.run_task(lambda: self._on_automation_error(str(e)))
    
    async def _on_automation_success(self):
        """Handle automation success."""
        self.log("✅ 上傳成功!")
        self.page.open(ft.SnackBar(ft.Text("✅ 處理完成!")))
        self._reset_dashboard()
    
    async def _on_automation_error(self, error: str):
        """Handle automation error."""
        self.log(f"❌ 錯誤: {error}")
        self.page.open(ft.SnackBar(ft.Text(f"❌ 錯誤: {error}")))
        self.process_btn.disabled = False
        self.page.update()
    
    def _reset_dashboard(self):
        """Reset dashboard for next file."""
        self.detected_file = None
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
        
        # Otoscopy
        self.left_clean = ft.RadioGroup(
            content=ft.Row([ft.Radio(value="True", label="是"), ft.Radio(value="False", label="否")]),
            value="True",
        )
        self.left_intact = ft.RadioGroup(
            content=ft.Row([ft.Radio(value="True", label="是"), ft.Radio(value="False", label="否")]),
            value="True",
        )
        self.right_clean = ft.RadioGroup(
            content=ft.Row([ft.Radio(value="True", label="是"), ft.Radio(value="False", label="否")]),
            value="True",
        )
        self.right_intact = ft.RadioGroup(
            content=ft.Row([ft.Radio(value="True", label="是"), ft.Radio(value="False", label="否")]),
            value="True",
        )
        
        self.build_dialog()
    
    def build_dialog(self):
        """Build the wizard dialog."""
        patient_name = self.session_info["patient_info"].get("Target_Patient_Name", "未知")
        birth_date = self.session_info["patient_info"].get("Patient_BirthDate", "")
        
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
            # Left ear
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("👂 左耳 Left", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN),
                        ft.Row([ft.Text("耳道乾淨：", width=100), self.left_clean]),
                        ft.Row([ft.Text("鼓膜完整：", width=100), self.left_intact]),
                    ]),
                    padding=15,
                    bgcolor=ft.Colors.GREEN_50,
                ),
            ),
            # Right ear
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("👂 右耳 Right", weight=ft.FontWeight.BOLD, color=ft.Colors.RED),
                        ft.Row([ft.Text("耳道乾淨：", width=100), self.right_clean]),
                        ft.Row([ft.Text("鼓膜完整：", width=100), self.right_intact]),
                    ]),
                    padding=15,
                    bgcolor=ft.Colors.RED_50,
                ),
            ),
        ], spacing=15)
        
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
            title=ft.Text("📋 聽力報告設定精靈"),
            content=self.content,
            actions=[
                self.prev_btn,
                ft.Container(expand=True),
                self.next_btn,
                self.submit_btn,
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
    
    def open(self):
        """Open the dialog."""
        self.page.open(self.dialog)
    
    def close(self):
        """Close the dialog."""
        self.page.close(self.dialog)
    
    def show_page(self, index: int):
        """Show specific page."""
        self.current_page = index
        
        if index == 0:
            self.content.content = self.page1
            self.prev_btn.visible = False
            self.next_btn.visible = True
            self.submit_btn.visible = False
        elif index == 1:
            self.content.content = self.page2
            self.prev_btn.visible = True
            self.next_btn.visible = True
            self.submit_btn.visible = False
        elif index == 2:
            self.update_summary()
            self.content.content = self.page3
            self.prev_btn.visible = True
            self.next_btn.visible = False
            self.submit_btn.visible = True
        
        self.page.update()
    
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
                "left_image": None,
                "right_image": None,
            }
        }
        self.close()
        self.on_complete(result)


def main(page: ft.Page):
    """Main entry point."""
    HearingApp(page)


if __name__ == "__main__":
    ft.app(target=main)
