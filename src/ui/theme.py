"""
UI Theme Configuration
Style: Glassmorphism / Modern Pro
"""
import flet as ft

class AppTheme:
    # --- Color Palette (Modern / Medical / Vibrant) ---
    # Primary: Medical Blue with Vibrancy
    PRIMARY = "#3B82F6"      # Blue 500
    PRIMARY_CONTAINER = "#DBEAFE" # Blue 100
    
    # Secondary: Modern Slate
    SECONDARY = "#64748B"    # Slate 500
    SECONDARY_CONTAINER = "#F1F5F9" # Slate 100
    
    # Backgrounds
    BACKGROUND = "#F0F4F8"   # Cool Grey / Alice Blue tone
    SURFACE = "#FFFFFF"      # White (Use with opacity for glass)
    
    # Text
    TEXT_PRIMARY = "#0F172A" # Slate 900
    TEXT_SECONDARY = "#475569" # Slate 600
    TEXT_HINT = "#94A3B8"    # Slate 400
    
    # Functional
    SUCCESS = "#10B981"      # Emerald 500
    WARNING = "#F59E0B"      # Amber 500
    ERROR = "#EF4444"        # Red 500
    INFO = "#0EA5E9"         # Sky 500
    
    # Sidebar
    SIDEBAR_BG = "#FFFFFF"
    
    # --- Shadows (Soft UI) ---
    SHADOW_SM = ft.BoxShadow(
        spread_radius=0, blur_radius=4, color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK), offset=ft.Offset(0, 2)
    )
    SHADOW_MD = ft.BoxShadow(
        spread_radius=0, blur_radius=10, color=ft.Colors.with_opacity(0.08, ft.Colors.BLACK), offset=ft.Offset(0, 4)
    )
    SHADOW_LG = ft.BoxShadow(
        spread_radius=0, blur_radius=20, color=ft.Colors.with_opacity(0.12, ft.Colors.BLACK), offset=ft.Offset(0, 8)
    )
    
    # --- Text Styles ---
    # Headings (Poppins-like)
    HEADER_TITLE = ft.TextStyle(
        size=28, 
        weight=ft.FontWeight.BOLD, 
        color=TEXT_PRIMARY,
        font_family="Segoe UI" # Fallback for Windows
    )
    
    SECTION_TITLE = ft.TextStyle(
        size=20, 
        weight=ft.FontWeight.W_600, 
        color=TEXT_PRIMARY,
        letter_spacing=0.5
    )
    
    BODY_TEXT = ft.TextStyle(
        size=15, 
        color=TEXT_PRIMARY,
        weight=ft.FontWeight.NORMAL
    )
    
    CAPTION = ft.TextStyle(
        size=12,
        color=TEXT_SECONDARY,
        weight=ft.FontWeight.NORMAL
    )

    @staticmethod
    def get_theme():
        # Customize the specific Flet theme properties
        return ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=AppTheme.PRIMARY,
                on_primary=ft.Colors.WHITE,
                primary_container=AppTheme.PRIMARY_CONTAINER,
                secondary=AppTheme.SECONDARY,
                secondary_container=AppTheme.SECONDARY_CONTAINER,
                background=AppTheme.BACKGROUND,
                surface=AppTheme.SURFACE,
                error=AppTheme.ERROR,
            ),
            use_material3=True,
            visual_density=ft.ThemeVisualDensity.COMFORTABLE,
            page_transitions=ft.PageTransitionsTheme(
                windows=ft.PageTransitionTheme.CUPERTINO
            ),
            font_family="Segoe UI", # Set global font to standard Windows font or Chinese equivalent
        )
