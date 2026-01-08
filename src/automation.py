"""
CRM Automation using Playwright
Handles login, store switching, patient search, and form filling.
"""
import asyncio
import time
import os
import shutil
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from src.config import FIELD_MAP, PROCESSED_FOLDER, FAILED_FOLDER


import traceback
from datetime import datetime

class HearingAutomation:
    """Hearing assessment CRM automation using Playwright."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._playwright = None
    
    def _log(self, message: str):
        """Print timestamped log message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [Auto] {message}")

    async def _save_screenshot(self, name_prefix: str):
        """Save debug screenshot."""
        if self.page:
            try:
                timestamp = int(time.time())
                filename = f"error_{name_prefix}_{timestamp}.png"
                await self.page.screenshot(path=filename, full_page=True)
                self._log(f"📸 Screenshot saved: {filename}")
            except Exception as e:
                self._log(f"Failed to save screenshot: {e}")

    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def start(self):
        """Start browser instance."""
        self._log("Starting browser...")
        self._playwright = await async_playwright().start()
        
        # Launch args for better visibility
        args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
        ]
        
        if not self.headless:
            args.append('--start-maximized')
            
        self.browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=args
        )
        
        # Set viewport to None for full window size if not headless
        viewport = None if not self.headless else {'width': 1920, 'height': 1080}
        
        self.context = await self.browser.new_context(
            viewport=viewport,
            no_viewport=True if not self.headless else False 
        )
        self.page = await self.context.new_page()
        self._log("Browser started successfully")
    
    async def close(self):
        """Close browser and cleanup."""
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._log("Browser closed")
    
    async def run_automation(self, data_payload: Dict[str, Any], xml_filepath: str, user_config: Dict[str, str]):
        """
        Main automation flow.
        """
        try:
            self._log(f"🚀 Starting automation for file: {os.path.basename(xml_filepath)}")
            
            url = user_config.get("url", "")
            username = user_config.get("username", "")
            password = user_config.get("password", "")
            store_id = user_config.get("store_id", "")
            
            # 1. Login
            if await self.navigate_and_login(url, username, password, store_id):
                # 2. Search patient
                patient_name = data_payload.get("Target_Patient_Name", "")
                birth_date = data_payload.get("Patient_BirthDate", "")
                
                if patient_name:
                    if not await self.search_patient(patient_name, birth_date):
                        raise Exception(f"無法找到病患: {patient_name}")
                
                # 3. Fill form
                await self.fill_form(data_payload)
                
                # 4. Submit
                await self.submit_form()
                
                # 5. Cleanup - move file to processed folder
                self._move_file_to_processed(xml_filepath)
                
                self._log("✅ Automation complete!")
            else:
                raise Exception("登入失敗")
                
        except Exception as e:
            self._log(f"❌ Automation error: {e}")
            self._log(f"Traceback:\n{traceback.format_exc()}")
            self._move_file_to_failed(xml_filepath)
            raise
    
    async def navigate_and_login(self, url: str, username: str, password: str, store_id: str = "") -> bool:
        """Navigate to CRM and login."""
        try:
            print(f"[Login] Navigating to {url}")
            print(f"[Login] Debug: Username='{username}', Password='{'***' if password else 'EMPTY'}'")
            await self.page.goto(url, wait_until='domcontentloaded')
            
            # Capture alert messages (e.g., "帳號密碼錯誤")
            self.last_alert_message = None
            async def handle_dialog(dialog):
                self.last_alert_message = dialog.message
                print(f"[Login] Alert Dialog: {dialog.message}")
                await dialog.accept()

            self.page.on("dialog", handle_dialog)

            # Fill login form
            await self.page.fill('#Acct', username)
            await self.page.fill('#Pwd', password)
            
            # Click login button
            await self.page.click('#Send')
            print("[Login] Clicked login button")
            
            # Wait for navigation or potential alert
            try:
                await self.page.wait_for_load_state('networkidle', timeout=10000)
            except:
                pass # Timeout OK if alert popped up blocking navigation?
            
            # Check if login successful (login form should be gone)
            if await self.page.locator('#Acct').count() > 0:
                print("[Login] Failed - login form still visible")
                if self.last_alert_message:
                    raise Exception(f"登入失敗: {self.last_alert_message}")
                return False
            
            print("[Login] Success!")
            
            # Handle store switch popup
            await self._handle_store_popup(store_id)
            
            return True
            
        except Exception as e:
            print(f"[Login] Error: {e}")
            return False
    
    async def _handle_store_popup(self, store_id: str = ""):
        """Handle store switch popup."""
        print(f"[Store] ========== STORE SWITCH DEBUG ==========")
        print(f"[Store] Received store_id parameter: '{store_id}'")
        print(f"[Store] store_id is truthy: {bool(store_id)}")
        
        try:
            # Wait for popup container
            popup_selector = '#switch-active-store-popup-body'
            popup = self.page.locator(popup_selector)
            
            try:
                await self.page.wait_for_selector(popup_selector, state='visible', timeout=5000)
                print("[Store] Popup found!")
                
                # Debug: Log current store shown in popup
                current_store = await self.page.text_content('.store_current')
                print(f"[Store] Currently displayed store: {current_store}")
                
            except:
                print("[Store] No popup found (timeout) - maybe already on correct store?")
                return
            
            if store_id:
                # Define selector
                select_selector = 'select[name="StoreSId"]'
                
                print(f"[Store] Attempting to select store: {store_id}")
                
                # CRITICAL: Search for ALL inputs (including hidden) that might contain store info
                form_debug = await self.page.evaluate(f'''() => {{
                    const popup = document.querySelector('#switch-active-store-popup-body');
                    if (!popup) return 'POPUP_NOT_FOUND';
                    
                    // Get all inputs in the popup
                    const allInputs = popup.querySelectorAll('input, select');
                    const inputs = [];
                    for (const inp of allInputs) {{
                        inputs.push({{
                            tag: inp.tagName,
                            name: inp.name,
                            type: inp.type || 'N/A',
                            value: inp.value
                        }});
                    }}
                    return JSON.stringify(inputs, null, 2);
                }}''')
                print(f"[Store] All form inputs in popup:\\n{form_debug}")
                
                # Update the select AND any hidden inputs with name containing 'Store'
                result = await self.page.evaluate(f'''() => {{
                    const popup = document.querySelector('#switch-active-store-popup-body');
                    if (!popup) return 'POPUP_NOT_FOUND';
                    
                    // Update select element
                    const select = popup.querySelector('{select_selector}');
                    if (select) {{
                        for (const opt of select.options) {{
                            opt.removeAttribute('selected');
                            opt.selected = false;
                        }}
                        const targetOption = Array.from(select.options).find(opt => opt.value === '{store_id}');
                        if (targetOption) {{
                            targetOption.setAttribute('selected', '');
                            targetOption.selected = true;
                        }}
                        select.value = '{store_id}';
                        select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                    
                    // CRITICAL: Also update ANY hidden input that might store the value
                    const hiddenInputs = popup.querySelectorAll('input[type="hidden"]');
                    for (const hidden of hiddenInputs) {{
                        if (hidden.name.toLowerCase().includes('store') || hidden.name === 'StoreSId') {{
                            hidden.value = '{store_id}';
                        }}
                    }}
                    
                    // Also check for data attributes on the button
                    const button = document.querySelector('#SwitchActiveStore');
                    if (button) {{
                        button.setAttribute('data-store-id', '{store_id}');
                    }}
                    
                    return 'SUCCESS: select=' + (select ? select.value : 'N/A');
                }}''')
                print(f"[Store] JS modification result: {result}")
                
                # Click switch button and wait for navigation
                try:
                    async with self.page.expect_navigation(timeout=10000):
                        await self.page.click('#SwitchActiveStore')
                except:
                    # Fallback: just wait for network idle
                    await self.page.wait_for_load_state('networkidle', timeout=5000)
                
            else:
                # No store_id provided, click Switch to proceed with default
                try:
                    await self.page.click('#SwitchActiveStore', force=True)
                    await popup.wait_for(state='hidden', timeout=5000)
                except:
                    pass
            
            print(f"[Store] Store switch completed")
                
        except Exception as e:
            print(f"[Store] ❌ Error in handler: {e}")
    
    async def search_patient(self, patient_name: str, birth_date: str, timeout: int = 30) -> bool:
        """Search for patient by name and birthday."""
        try:
            print(f"[Search] Looking for: {patient_name}, DOB: {birth_date}")
            
            # Click "使用姓名+生日搜尋客戶" tab with retry logic
            tab_selector = 'text=使用姓名+生日搜尋客戶'
            target_field = 'input[name="QName"]'
            
            for attempt in range(3):
                try:
                    self._log(f"[Search] Clicking tab: {tab_selector} (Attempt {attempt+1}/3)")
                    
                    # Try to find and click the tab
                    await self.page.click(tab_selector, timeout=5000)
                    
                    # Wait briefly to see if field appears
                    try:
                        await self.page.wait_for_selector(target_field, state='visible', timeout=5000)
                        self._log("[Search] Target field found!")
                        break # Success
                    except:
                        if attempt == 2:
                            raise # Re-raise if last attempt failed
                        self._log(f"[Search] Field {target_field} not visible yet, retrying click...")
                        await self.page.wait_for_timeout(500)
                        
                except Exception as e:
                    if attempt == 2:
                        raise e
            
            # Fill customer name
            await self.page.fill('input[name="QName"]', patient_name)
            
            # Fill birthday if provided
            if birth_date:
                self._log(f"[Search] Filling birthday: {birth_date}")
                parts = birth_date.split('-')
                if len(parts) == 3:
                    # Birthday fields are SELECT elements, use select_option
                    # Year
                    await self.page.select_option('select[name="QBirthdayY"]', parts[0])
                    # Month (remove leading zero for value matching if needed, but select_option handles text/value)
                    # The HTML values are "1", "2"... "12", so we strip '0'
                    await self.page.select_option('select[name="QBirthdayM"]', parts[1].lstrip('0'))
                    # Day
                    # HTML shows empty day initially, but it should populate. 
                    # We might need to handle dynamic population of days?
                    # Usually selecting Y and M updates D. 
                    await self.page.select_option('select[name="QBirthdayD"]', parts[2].lstrip('0'))
            
            # Match older logic: Click search button
            self._log("[Search] Clicking search button...")
            try:
                # Correct button provided by user: <button type="button" name="SearchByPhone" value="SearchByPhone">客戶資料查詢</button>
                # Using name or text. Since locator resolved to 2 elements and first was invisible, we need to filter.
                
                search_btns = self.page.locator('button[name="SearchByPhone"], button:has-text("客戶資料查詢")')
                count = await search_btns.count()
                
                clicked = False
                for i in range(count):
                    btn = search_btns.nth(i)
                    if await btn.is_visible():
                        self._log(f"[Search] Found visible button at index {i}, clicking...")
                        await btn.click()
                        clicked = True
                        break
                
                if not clicked:
                    self._log("[Search] No visible button found via specific selector, trying fallback...")
                    raise Exception("No visible specific button")

            except Exception as e:
                self._log(f"[Search] Retrying search button click with fallback... {e}")
                # Try generic fallback but also check visibility
                await self.page.click('#SearchCustNameBirth', force=True) # Last resort
                
            self._log("[Search] Search submitted")
            
            # Find patient link - Robust Strategy
            # 1. Try generic text match in a table cell or link
            try:
                # Locator for any element containing the name
                results = self.page.locator(f'text={patient_name}')
                count = await results.count()
                self._log(f"[Search] Found {count} elements matching name '{patient_name}'")
                
                target_link = None
                
                if count > 0:
                    # Iterate to find a clickable link
                    for i in range(count):
                        el = results.nth(i)
                        
                        # Check if it's a link or inside a link
                        is_link = await el.evaluate("el => el.tagName === 'A' || el.closest('a') !== null")
                        
                        if is_link:
                            target_link = el
                            break
                        
                        # If it's a TD, maybe the link is inside or it's just text.
                        # Try to click it anyway if it looks like a result row?
                        # Better to find key columns.
                
                if target_link:
                     self._log(f"[Search] Found clickable link for: {patient_name}")
                     await target_link.click()
                     await self.page.wait_for_load_state('networkidle')
                     
                     # Navigate to hearing report page
                     await self._navigate_to_hearing_report()
                     return True
                else:
                    self._log(f"[Search] Patient name found but not clickable link?")
            except Exception as e:
                 self._log(f"[Search] Error finding patient link: {e}")

            self._log(f"[Search] Patient not found: {patient_name}")
            return False
                
        except Exception as e:
            self._log(f"[Search] Error: {e}")
            return False
    
    async def _navigate_to_hearing_report(self):
        """Navigate to hearing report form page."""
        try:
            self._log("[Navigate] Navigating to Hearing Report tab...")
            
            # User provided: <a href="/czhearingreport?custSId=...">聽力報告</a>
            
            # Target the link with text "聽力報告"
            # Using specific locator to avoid ambiguity
            report_link = self.page.locator('a:has-text("聽力報告")')
            
            if await report_link.count() > 0:
                # Click the first visible one
                await report_link.first.click(force=True)
                self._log("[Navigate] Clicked '聽力報告' link")
            else:
                # Fallback to href check
                self._log("[Navigate] Link by text not found, trying href...")
                await self.page.click('a[href*="czhearingreport"]', force=True)
                self._log("[Navigate] Clicked link via href")
                
            await self.page.wait_for_load_state('networkidle')
            
            # Step 2: Click "新增聽力報告" (Add Hearing Report)
            # User provided: <a href="..." class="add_hearing_rep">新增聽力報告</a>
            self._log("[Navigate] Waiting for 'Add Hearing Report' button...")
            add_btn = self.page.locator('a.add_hearing_rep, a:has-text("新增聽力報告")')
            
            try:
                # Wait for button to be visible (give it a moment if list checks execute fast)
                await add_btn.wait_for(state='visible', timeout=5000)
                await add_btn.click()
                self._log("[Navigate] Clicked '新增聽力報告'")
                await self.page.wait_for_load_state('networkidle')
            except Exception as e:
                self._log(f"[Navigate] Warning: Could not click 'Add' button (maybe already on form?): {e}")
                # We don't raise here immediately, in case we are already on the form page, 
                # but usually we need to click it.
                raise e
            
        except Exception as e:
            self._log(f"[Navigate] Error: {e}")
            raise e
    
    async def fill_form(self, data: Dict[str, Any]):
        """Fill the hearing assessment form."""
        self._log(f"[Form] Filling form with {len(data)} fields")
        
        # Fill other fields from FIELD_MAP
        for field in FIELD_MAP:
            try:
                key = field.get("key")
                if not key or key not in data:
                    continue
                
                data_value = data[key]
                if data_value is None or data_value == "":
                    continue
                
                # Construct Selector
                selector_type = field.get("selector_type", "")
                selector_value = field.get("selector_value", "")
                
                if not selector_value:
                    continue
                    
                selector = ""
                if selector_type == "ID":
                    selector = f"#{selector_value}"
                elif selector_type == "Name":
                    selector = f"[name='{selector_value}']"
                elif selector_type == "Class":
                    selector = f".{selector_value}"
                else:
                    selector = selector_value # Fallback
                
                input_type = field.get("input_type", "Text")
                
                # Handle different input types
                if input_type in ["Text", "Textarea"]:
                    await self.page.fill(selector, str(data_value))
                    
                elif input_type == "Select":
                    await self.page.select_option(selector, str(data_value))
                    
                elif input_type == "Radio":
                    # For radio, we check if the data_value matches the 'value_match'
                    value_match = field.get("value_match")
                    
                    # specific boolean conversion for comparison
                    str_data_val = str(data_value).lower()
                    str_match_val = str(value_match).lower()
                    
                    # Handle python bool string "True"/"False" vs "true"/"false"
                    if str_data_val == str_match_val:
                        await self.page.click(selector)
                        self._log(f"[Form] Clicked Radio {key}: {selector} (Match: {data_value})")
                    else:
                        continue # Skip if this radio doesn't match the value
                        
                elif input_type == "File":
                     # Handle file upload
                     if os.path.exists(str(data_value)):
                         await self.page.set_input_files(selector, str(data_value))
                         self._log(f"[Form] Uploaded file for {key}: {data_value}")
                     else:
                         self._log(f"[Form] ⚠️ File not found for {key}: {data_value}")
                         continue
                
                if input_type != "Radio":
                    self._log(f"[Form] Filled {key}: {data_value}")
                
            except Exception as e:
                self._log(f"[Form] Error filling {field.get('key', '?')}: {e}")
        
        self._log("[Form] Form fill complete")
    
    async def submit_form(self):
        """Submit the form."""
        try:
            submit_btn = self.page.locator('.submit button#Send, button#Send')
            await submit_btn.click()
            print("[Submit] Form submitted!")
            
            # Wait for submission to complete
            await self.page.wait_for_timeout(3000)
        except Exception as e:
            print(f"[Submit] Error: {e}")
            raise
    
    def _move_file_to_processed(self, filepath: str):
        """Move processed file to processed folder relative to source file."""
        try:
            source_dir = os.path.dirname(filepath)
            processed_dir = os.path.join(source_dir, "processed")
            
            if not os.path.exists(processed_dir):
                os.makedirs(processed_dir)
            
            filename = os.path.basename(filepath)
            dest = os.path.join(processed_dir, filename)
            
            # Handle duplicate filenames
            if os.path.exists(dest):
                base, ext = os.path.splitext(filename)
                timestamp = int(time.time())
                dest = os.path.join(processed_dir, f"{base}_{timestamp}{ext}")
            
            shutil.move(filepath, dest)
            print(f"[Cleanup] Moved to processed: {os.path.basename(dest)}")
        except Exception as e:
            print(f"[Cleanup] Error moving file: {e}")
    
    def _move_file_to_failed(self, filepath: str):
        """Move failed file to failed folder relative to source file."""
        try:
            source_dir = os.path.dirname(filepath)
            failed_dir = os.path.join(source_dir, "failed")
            
            if not os.path.exists(failed_dir):
                os.makedirs(failed_dir)
            
            filename = os.path.basename(filepath)
            dest = os.path.join(failed_dir, filename)
            
            # Handle duplicate filenames
            if os.path.exists(dest):
                base, ext = os.path.splitext(filename)
                timestamp = int(time.time())
                dest = os.path.join(failed_dir, f"{base}_{timestamp}{ext}")
            
            shutil.move(filepath, dest)
            print(f"[Cleanup] Moved to failed: {os.path.basename(dest)}")
        except Exception as e:
            print(f"[Cleanup] Error moving file: {e}")


# Synchronous wrapper for backward compatibility
def run_automation_sync(data_payload: Dict[str, Any], xml_filepath: str, user_config: Dict[str, str], headless: bool = True):
    """Synchronous wrapper to run automation."""
    async def _run():
        async with HearingAutomation(headless=headless) as auto:
            await auto.run_automation(data_payload, xml_filepath, user_config)
    
    asyncio.run(_run())
