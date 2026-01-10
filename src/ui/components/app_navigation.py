"""
Navigation Rail Component
"""
import flet as ft
from src.ui.theme import AppTheme

class AppNavigation(ft.NavigationRail):
    def __init__(self, on_change):
        super().__init__()
        self.selected_index = 0
        self.label_type = ft.NavigationRailLabelType.ALL
        self.min_width = 100
        self.min_extended_width = 200
        self.group_alignment = -0.9
        self.bgcolor = AppTheme.SURFACE
        
        # Style
        self.indicator_color = AppTheme.PRIMARY_CONTAINER
        self.indicator_shape = ft.CircleBorder() # Modern round indicator
        self.selected_icon_color = AppTheme.PRIMARY
        self.unselected_icon_color = AppTheme.SECONDARY
        self.selected_label_text_style = ft.TextStyle(color=AppTheme.PRIMARY, weight=ft.FontWeight.BOLD)
        self.unselected_label_text_style = ft.TextStyle(color=AppTheme.SECONDARY)
        
        self.destinations = [
            ft.NavigationRailDestination(
                icon=ft.Icons.DASHBOARD_OUTLINED,
                selected_icon=ft.Icons.DASHBOARD_ROUNDED,
                label="儀表板"
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS_ROUNDED,
                label="設定"
            ),
        ]
        self.on_change = on_change
