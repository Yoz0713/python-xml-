import flet as ft
import datetime
from src.ui.theme import AppTheme

class ActivityLog(ft.Container):
    def __init__(self):
        super().__init__()
        
        self.log_list = ft.ListView(spacing=5, expand=True, auto_scroll=True)
        
        self.content = ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.HISTORY, color=AppTheme.PRIMARY),
                ft.Text("系統活動紀錄", size=16, weight=ft.FontWeight.BOLD)
            ], spacing=10),
            ft.Divider(),
            self.log_list
        ], expand=True)
        
        self.bgcolor = AppTheme.SURFACE
        self.padding = 20
        self.border_radius = 12
        self.expand = True

    def add_log(self, message: str, type: str = "info"):
        icon_map = {
            "info": (ft.Icons.INFO, AppTheme.INFO),
            "success": (ft.Icons.CHECK_CIRCLE, AppTheme.SUCCESS),
            "error": (ft.Icons.ERROR, AppTheme.ERROR),
            "warning": (ft.Icons.WARNING, AppTheme.WARNING)
        }
        icon_name, icon_color = icon_map.get(type, icon_map["info"])
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        item = ft.Row([
            ft.Text(timestamp, size=11, color=AppTheme.TEXT_HINT),
            ft.Icon(icon_name, size=16, color=icon_color),
            ft.Text(message, size=13, expand=True),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        
        self.log_list.controls.append(item)
        
        if self.page:
            self.log_list.update()
