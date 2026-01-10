import flet as ft
from src.ui.theme import AppTheme

class StatCard(ft.Container):
    def __init__(self, title: str, value: str, icon, color):
        super().__init__()
        
        self.value_text = ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_PRIMARY)
        
        self.icon_container = ft.Container(
            content=ft.Icon(icon, color=ft.Colors.WHITE, size=24),
            padding=12,
            bgcolor=color,
            border_radius=10
        )
        
        self.content = ft.Row([
            self.icon_container,
            ft.Column([
                ft.Text(title, size=13, color=AppTheme.TEXT_SECONDARY),
                self.value_text,
            ], spacing=2, alignment=ft.MainAxisAlignment.CENTER),
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)
        
        self.padding = 20
        self.bgcolor = AppTheme.SURFACE
        self.border_radius = 12
        self.expand = True

    def update_value(self, new_value: str):
        self.value_text.value = new_value
