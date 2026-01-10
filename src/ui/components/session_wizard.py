"""
Session Wizard Component
Multi-page wizard dialog for session selection and upload configuration.
"""
import flet as ft
from typing import Dict, Any, Callable, Optional

class SessionWizard:
    """Multi-page wizard dialog for session selection."""
    
    def __init__(self, page: ft.Page, session_info: Dict, on_complete: Callable):
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
        
        # Ear image paths
        self.left_image_path = None
        self.right_image_path = None
        self.left_image_text = ft.Text("未選擇檔案", size=12, color=ft.Colors.GREY_400)
        self.right_image_text = ft.Text("未選擇檔案", size=12, color=ft.Colors.GREY_400)
        
        self.left_file_picker = ft.FilePicker(on_result=self.on_left_image_picked)
        self.right_file_picker = ft.FilePicker(on_result=self.on_right_image_picked)
        self.page.overlay.extend([self.left_file_picker, self.right_file_picker])

        # Otoscopy radio groups
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
        
        # --- Google Sheets Integration Fields ---
        self.sheets_configured = bool(session_info.get("spreadsheet_id"))
        
        self.sheets_checkbox = ft.Checkbox(
            label="同時寫入 Google 試算表",
            value=False,
            on_change=self._toggle_sheets_fields,
        )
        
        # Customer source options
        self.customer_source_options = [
            "門市轉介", "員工本人", "員工家屬", "門市DM/海報", "招牌", 
            "過路客", "自邀客", "舊客轉介", "GOOGLE", "FB/LINE", 
            "聽篩活動", "門市聽篩(蓋門市聽篩章)", "簡訊廣告"
        ]
        
        self.customer_source_checkboxes = {}
        for option in self.customer_source_options:
            self.customer_source_checkboxes[option] = ft.Checkbox(
                label=option, 
                value=False,
                on_change=self._update_customer_source_display,
            )
        
        # Invitation card and is deal options
        invitation_card_options = ["有", "無"]
        is_deal_options = ["是", "否"]
        
        # Fields for Google Sheets
        self.sheets_phone = ft.TextField(label="電話", prefix_icon=ft.Icons.PHONE)
        
        self.customer_source_display = ft.TextField(
            label="顧客來源 (可複選)",
            read_only=True,
            prefix_icon=ft.Icons.SOURCE,
            hint_text="點擊選擇...",
        )
        
        self.customer_source_popup = ft.PopupMenuButton(
            icon=ft.Icons.ARROW_DROP_DOWN,
            items=[
                ft.PopupMenuItem(content=self.customer_source_checkboxes[opt]) 
                for opt in self.customer_source_options
            ],
            tooltip="選擇顧客來源",
        )
        
        self.sheets_customer_source_container = ft.Container(
            content=ft.Row([
                ft.Container(self.customer_source_display, expand=True),
                self.customer_source_popup,
            ]),
        )
        
        self.sheets_clinic_name = ft.TextField(label="診所名稱 (選填)", prefix_icon=ft.Icons.LOCAL_HOSPITAL)
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
        
        self.sheets_transaction_amount = ft.TextField(
            label="成交金額 (U欄)",
            prefix_icon=ft.Icons.ATTACH_MONEY,
            visible=False,
        )
        
        # Conditional fields for invitation card
        self.sheets_store_code = ft.TextField(label="門市編號 (K欄)", prefix_icon=ft.Icons.STORE)
        self.sheets_recommend_id = ft.TextField(label="推薦人工號 (M欄)", prefix_icon=ft.Icons.BADGE)
        self.sheets_voucher_count = ft.TextField(label="金鑽券發放張數 (R欄)", prefix_icon=ft.Icons.CONFIRMATION_NUMBER)
        self.sheets_voucher_id = ft.TextField(label="金鑽券發放編號 (S欄)", prefix_icon=ft.Icons.NUMBERS)
        
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
        patient_name = self.session_info.get("patient_info", {}).get("Target_Patient_Name", "未知")
        birth_date = self.session_info.get("patient_info", {}).get("Patient_BirthDate", "")
        
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
                        ft.Text("👂 左耳 Left", weight=ft.FontWeight.BOLD, size=16),
                        ft.Divider(),
                        ft.Row([ft.Text("耳道乾淨：", width=100), self.left_clean]),
                        ft.Row([ft.Text("鼓膜完整：", width=100), self.left_intact]),
                        ft.Divider(),
                        ft.Row([
                            ft.ElevatedButton("上傳左耳圖", icon=ft.Icons.UPLOAD_FILE, 
                                            on_click=lambda _: self.left_file_picker.pick_files(allow_multiple=False)),
                            self.left_image_text
                        ])
                    ]),
                    padding=15,
                    bgcolor=ft.Colors.BLUE_900,
                    border_radius=10,
                ),
            ),
            # Right ear
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("👂 右耳 Right", weight=ft.FontWeight.BOLD, size=16),
                        ft.Divider(),
                        ft.Row([ft.Text("耳道乾淨：", width=100), self.right_clean]),
                        ft.Row([ft.Text("鼓膜完整：", width=100), self.right_intact]),
                        ft.Divider(),
                        ft.Row([
                            ft.ElevatedButton("上傳右耳圖", icon=ft.Icons.UPLOAD_FILE, 
                                            on_click=lambda _: self.right_file_picker.pick_files(allow_multiple=False)),
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
        
        page3_content = [
            ft.Text("步驟 3/3：確認並送出", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE),
            ft.Card(
                content=ft.Container(
                    content=self.summary_text,
                    padding=20,
                ),
            ),
        ]
        
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
                )
            )
        
        self.page3 = ft.Column(page3_content, spacing=15, scroll=ft.ScrollMode.AUTO)
        
        # Content container
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
        actions = self.dialog.actions
        actions.clear()
        
        if index == 0:
            self.content.content = self.page1
            self.prev_btn.visible = False
            self.next_btn.visible = True
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
    
    def update_summary(self):
        """Update summary text."""
        patient_name = self.session_info.get("patient_info", {}).get("Target_Patient_Name", "")
        summary = f"""病患: {patient_name}
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
        """Toggle visibility of Google Sheets fields."""
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
        """Update the customer source display field."""
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
        self.page.close(self.dialog)
        self.on_complete(result)
