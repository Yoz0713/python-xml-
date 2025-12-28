"""
大樹聽中行政自動化 - Main Entry Point
Run this file to start the application.
"""
import sys
import os
import traceback


def main_entry():
    """Main entry point with comprehensive error handling."""
    error_log_path = None
    
    try:
        # Set up error log path first
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            base_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        error_log_path = os.path.join(base_dir, "error_log.txt")
        
        # Try importing and running
        import flet as ft
        from src.gui import main
        ft.app(target=main)
        
    except Exception as e:
        # Build error message
        error_msg = f"Application startup error:\n{traceback.format_exc()}"
        
        # Write to log file
        if error_log_path:
            try:
                with open(error_log_path, "w", encoding="utf-8") as f:
                    f.write(error_msg)
            except:
                pass
        
        # Print to console and wait for user input
        print("=" * 60)
        print("應用程式啟動錯誤 / Application Startup Error")
        print("=" * 60)
        print(error_msg)
        print("=" * 60)
        if error_log_path:
            print(f"錯誤日誌已保存到: {error_log_path}")
        print("按 Enter 鍵關閉 / Press Enter to close...")
        
        try:
            input()
        except:
            import time
            time.sleep(10)  # Fallback: wait 10 seconds
        
        sys.exit(1)


if __name__ == "__main__":
    main_entry()
