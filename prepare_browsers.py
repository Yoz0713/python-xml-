import os
import shutil
import glob
from pathlib import Path

def prepare_browsers():
    print("正在尋找 Playwright 瀏覽器...")
    
    # Locate Playwright browsers path
    # Usually in %USERPROFILE%\AppData\Local\ms-playwright
    local_app_data = os.environ.get('LOCALAPPDATA')
    if not local_app_data:
        print("❌ 無法找到 LocalAppData 路徑")
        return

    playwright_path = Path(local_app_data) / "ms-playwright"
    
    if not playwright_path.exists():
        print(f"❌ 找不到 Playwright 資料夾: {playwright_path}")
        print("請嘗試執行: playwright install chromium")
        return

    print(f"✅ 找到 Playwright 資料夾: {playwright_path}")

    # Find chromium folder
    chromium_folders = list(playwright_path.glob("chromium-*"))
    
    if not chromium_folders:
        print("❌ 找不到 Chromium 瀏覽器")
        return

    # Use the latest one if multiple
    source_browser = chromium_folders[-1]
    print(f"✅ 選擇瀏覽器: {source_browser.name}")

    # Target directory in current project
    target_dir = Path("dist/browsers")
    
    # Create target directory
    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ 建立目標資料夾: {target_dir}")

    target_browser_path = target_dir / source_browser.name
    
    # Copy
    if target_browser_path.exists():
        print("⚠️ 目標瀏覽器已存在，跳過複製")
    else:
        print(f"📦 正在複製瀏覽器 (這可能需要一點時間)...")
        print(f"   從: {source_browser}")
        print(f"   到: {target_browser_path}")
        try:
            shutil.copytree(source_browser, target_browser_path)
            print("✨ 複製完成！")
        except Exception as e:
            print(f"❌ 複製失敗: {e}")
            return

    print("\n" + "="*50)
    print("🎉 準備完成！")
    print("="*50)
    print("請依照以下結構發布您的程式：")
    print(f"📂 您的資料夾/")
    print(f"  ├── 📄 Main.exe (您打包好的程式)")
    print(f"  └── 📂 browsers/")
    print(f"       └── 📂 {source_browser.name} (剛剛複製的資料夾)")
    print("="*50)

if __name__ == "__main__":
    prepare_browsers()
