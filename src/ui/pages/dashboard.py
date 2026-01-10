import flet as ft
import os
from src.ui.theme import AppTheme
from src.ui.components.stat_card import StatCard
from src.ui.components.activity_log import ActivityLog

class DashboardPage(ft.Container):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 20
        self.bgcolor = AppTheme.BACKGROUND
        
        # File queue storage
        self.pending_files = []  # List of file paths in queue
        self.selected_file = None  # Currently selected file
        
        # --- Monitor Button (integrated into header) ---
        self.monitor_btn = ft.ElevatedButton(
            "啟動監控",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self.toggle_monitoring_click,
            bgcolor=AppTheme.SUCCESS,
            color=ft.Colors.WHITE,
            height=40,
        )
        
        # --- Account & Store Status Badges ---
        self.account_badge = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.PERSON, size=16, color=AppTheme.PRIMARY),
                ft.Text(self.app.active_profile_name or "未選擇帳號", size=12, color=AppTheme.TEXT_PRIMARY),
            ], spacing=6),
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            bgcolor=AppTheme.PRIMARY_CONTAINER,
            border_radius=16,
        )
        
        self.store_badge = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.STORE, size=16, color=AppTheme.WARNING),
                ft.Text(self.app.store_id or "不切換 (使用預設)", size=12, color=AppTheme.TEXT_PRIMARY),
            ], spacing=6),
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.with_opacity(0.15, AppTheme.WARNING),
            border_radius=16,
        )
        
        # --- Header with integrated controls ---
        self.folder_text = ft.Text(
            self.app.watch_path or "尚未選擇資料夾...", 
            size=13, 
            color=AppTheme.TEXT_SECONDARY,
            width=200,
            no_wrap=True
        )
        
        self.header = ft.Container(
            content=ft.Column([
                ft.Row([
                    # Title section
                    ft.Column([
                        ft.Text("儀表板", size=24, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_PRIMARY),
                        ft.Row([
                            self.account_badge,
                            self.store_badge,
                        ], spacing=8),
                    ], spacing=6),
                    ft.Container(expand=True),
                    # Controls section - folder + monitor button
                    ft.Row([
                        ft.Icon(ft.Icons.FOLDER_OPEN, color=AppTheme.PRIMARY, size=18),
                        self.folder_text,
                        ft.ElevatedButton(
                            "更換", 
                            on_click=lambda _: self.app.pick_folder(),
                            bgcolor=AppTheme.SECONDARY,
                            color=ft.Colors.WHITE,
                            height=32,
                        ),
                        ft.VerticalDivider(width=15, color=ft.Colors.GREY_300),
                        self.monitor_btn,
                    ], spacing=8, alignment=ft.MainAxisAlignment.END),
                ]),
            ]),
            padding=15,
            bgcolor=AppTheme.SURFACE,
            border_radius=12
        )
        
        # --- Status Cards ---
        self.status_card_mon = StatCard("監控狀態", "已停止", ft.Icons.STOP_CIRCLE, AppTheme.SECONDARY)
        self.status_card_sheet = StatCard("Google 試算表", "未連線", ft.Icons.TABLE_CHART, AppTheme.WARNING)
        
        self.cards_row = ft.Row([
            self.status_card_mon,
            self.status_card_sheet,
        ], spacing=15)
        
        # --- Patient Card (Selected File Info) ---
        self.patient_name = ft.Text("等待選擇 XML 檔案...", size=18, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_PRIMARY)
        self.patient_info = ft.Text("", size=13, color=AppTheme.TEXT_SECONDARY)
        
        self.process_btn = ft.ElevatedButton(
            "設定並上傳",
            icon=ft.Icons.UPLOAD,
            on_click=self.on_process_click,
            bgcolor=AppTheme.SUCCESS,
            color=ft.Colors.WHITE,
            disabled=True,
            height=42
        )
        
        self.patient_card = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.PERSON, size=36, color=AppTheme.PRIMARY),
                ft.Column([
                    self.patient_name,
                    self.patient_info,
                ], spacing=2, expand=True),
                self.process_btn
            ]),
            padding=18,
            bgcolor=AppTheme.SURFACE,
            border_radius=12
        )
        
        # --- Pending File Queue ---
        self.pending_list_view = ft.ListView(spacing=5, expand=True)
        self.file_count_text = ft.Text("0 個檔案", size=12, color=AppTheme.TEXT_HINT)
        
        self.pending_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.QUEUE, color=AppTheme.PRIMARY),
                    ft.Text("待處理清單", size=16, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    self.file_count_text
                ], spacing=10),
                ft.Divider(),
                ft.Text("點擊檔案可選擇上傳", size=11, color=AppTheme.TEXT_HINT, italic=True),
                self.pending_list_view
            ], expand=True),
            padding=18,
            bgcolor=AppTheme.SURFACE,
            border_radius=12,
            expand=True
        )
        
        # --- Activity Log ---
        self.activity_log = ActivityLog()
        
        self.bottom_row = ft.Row([
            ft.Container(content=self.pending_card, expand=1),
            ft.Container(content=self.activity_log, expand=1)
        ], spacing=15, expand=True)

        # --- Assemble Layout (removed action_row) ---
        self.content = ft.Column([
            self.header,
            ft.Container(height=12),
            self.cards_row,
            ft.Container(height=12),
            self.patient_card,
            ft.Container(height=12),
            self.bottom_row
        ], expand=True)

    def toggle_monitoring_click(self, e):
        self.app.toggle_monitoring()

    def on_process_click(self, e):
        """Handle process button click - trigger upload wizard."""
        if self.selected_file:
            self.app.open_wizard(self.selected_file)

    def update_status(self, is_monitoring: bool):
        if is_monitoring:
            self.status_card_mon.update_value("監控中")
            self.status_card_mon.icon_container.bgcolor = AppTheme.SUCCESS
            self.status_card_mon.icon_container.content.name = ft.Icons.RADAR
            self.monitor_btn.text = "停止監控"
            self.monitor_btn.icon = ft.Icons.STOP
            self.monitor_btn.bgcolor = AppTheme.ERROR
        else:
            self.status_card_mon.update_value("已停止")
            self.status_card_mon.icon_container.bgcolor = AppTheme.SECONDARY
            self.status_card_mon.icon_container.content.name = ft.Icons.STOP_CIRCLE
            self.monitor_btn.text = "啟動監控"
            self.monitor_btn.icon = ft.Icons.PLAY_ARROW
            self.monitor_btn.bgcolor = AppTheme.SUCCESS
            
        self.monitor_btn.update()
        self.status_card_mon.update()
        
    def update_folder(self, path: str):
        self.folder_text.value = path if path else "尚未選擇資料夾..."
        if self.page:
            self.folder_text.update()

    def log(self, message: str, type: str = "info"):
        self.activity_log.add_log(message, type)

    def set_sheet_status(self, connected: bool, name: str):
        if connected:
            self.status_card_sheet.update_value("已連線")
            self.status_card_sheet.icon_container.bgcolor = AppTheme.SUCCESS
            self.status_card_sheet.icon_container.content.name = ft.Icons.TABLE_CHART
        else:
            self.status_card_sheet.update_value("未連線")
            self.status_card_sheet.icon_container.bgcolor = AppTheme.WARNING
            self.status_card_sheet.icon_container.content.name = ft.Icons.TABLE_CHART
        self.status_card_sheet.update()
    
    def update_account_badge(self, profile_name: str):
        """Update account badge with current profile name."""
        text = self.account_badge.content.controls[1]
        text.value = profile_name if profile_name else "未選擇帳號"
        if self.page:
            self.account_badge.update()
    
    def update_store_badge(self, store_name: str):
        """Update store badge with current store name."""
        text = self.store_badge.content.controls[1]
        text.value = store_name if store_name else "不切換 (使用預設)"
        if self.page:
            self.store_badge.update()

    def add_file_to_queue(self, file_path: str):
        """Add a file to the pending queue if not already present."""
        if file_path in self.pending_files:
            return  # Already in queue
        
        self.pending_files.append(file_path)
        self._refresh_pending_list()
        
        # Auto-select first file if nothing selected
        if self.selected_file is None:
            self.select_file(file_path)
    
    def remove_file_from_queue(self, file_path: str):
        """Remove a file from the pending queue."""
        if file_path not in self.pending_files:
            return
        
        self.pending_files.remove(file_path)
        
        # Clear selection if the removed file was selected
        if self.selected_file == file_path:
            self.selected_file = None
            self._reset_patient_card()
        
        self._refresh_pending_list()
    
    def select_file(self, file_path: str):
        """Select a file from the queue for processing."""
        if file_path not in self.pending_files:
            return
            
        self.selected_file = file_path
        filename = os.path.basename(file_path)
        
        # Update patient card
        self.patient_name.value = f"已選擇: {filename}"
        self.patient_info.value = f"路徑: {file_path}"
        self.process_btn.disabled = False
        
        # Refresh list to show selection highlight
        self._refresh_pending_list()
        
        # Update UI
        if self.page:
            self.patient_name.update()
            self.patient_info.update()
            self.process_btn.update()
        
        # Trigger file load in app
        self.app.on_file_selected(file_path)
    
    def _reset_patient_card(self):
        """Reset patient card to default state."""
        self.patient_name.value = "等待選擇 XML 檔案..."
        self.patient_info.value = ""
        self.process_btn.disabled = True
        
        if self.page:
            self.patient_name.update()
            self.patient_info.update()
            self.process_btn.update()
    
    def _refresh_pending_list(self):
        """Refresh the pending file list UI."""
        self.pending_list_view.controls.clear()
        
        if not self.pending_files:
            self.pending_list_view.controls.append(
                ft.Text("尚無待處理檔案", color=AppTheme.TEXT_HINT, italic=True, size=13)
            )
        else:
            for file_path in self.pending_files:
                is_selected = (file_path == self.selected_file)
                filename = os.path.basename(file_path)
                
                item = ft.Container(
                    content=ft.Row([
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE if is_selected else ft.Icons.DESCRIPTION,
                            size=18,
                            color=AppTheme.SUCCESS if is_selected else AppTheme.TEXT_SECONDARY
                        ),
                        ft.Text(
                            filename,
                            size=13,
                            expand=True,
                            no_wrap=True,
                            weight=ft.FontWeight.BOLD if is_selected else None,
                            color=AppTheme.SUCCESS if is_selected else AppTheme.TEXT_PRIMARY
                        ),
                        ft.Text(
                            "已選擇" if is_selected else "",
                            size=10,
                            color=AppTheme.SUCCESS,
                            italic=True
                        ) if is_selected else ft.Container()
                    ], spacing=10),
                    padding=10,
                    border_radius=8,
                    bgcolor=AppTheme.PRIMARY_CONTAINER if is_selected else AppTheme.BACKGROUND,
                    border=ft.border.all(2, AppTheme.SUCCESS) if is_selected else None,
                    on_click=lambda e, fp=file_path: self.select_file(fp),
                    ink=True
                )
                self.pending_list_view.controls.append(item)
        
        # Update file count
        self.file_count_text.value = f"{len(self.pending_files)} 個檔案"
        
        if self.page:
            self.pending_list_view.update()
            self.file_count_text.update()
    
    def clear_queue(self):
        """Clear all files from the queue."""
        self.pending_files.clear()
        self.selected_file = None
        self._reset_patient_card()
        self._refresh_pending_list()
    
    def update_patient_info(self, name: str, info: str):
        """Update patient card with parsed info."""
        self.patient_name.value = name
        self.patient_info.value = info
        self.process_btn.disabled = False
        
        if self.page:
            self.patient_name.update()
            self.patient_info.update()
            self.process_btn.update()
    
    def mark_file_processed(self, file_path: str):
        """Mark a file as processed and remove from queue."""
        self.remove_file_from_queue(file_path)
        self.log(f"已處理: {os.path.basename(file_path)}", "success")
