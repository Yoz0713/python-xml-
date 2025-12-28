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


class HearingAutomation:
    """Hearing assessment CRM automation using Playwright."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._playwright = None
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def start(self):
        """Start browser instance."""
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ]
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await self.context.new_page()
        print("[Playwright] Browser started")
    
    async def close(self):
        """Close browser and cleanup."""
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
        print("[Playwright] Browser closed")
    
    async def run_automation(self, data_payload: Dict[str, Any], xml_filepath: str, user_config: Dict[str, str]):
        """
        Main automation flow.
        """
        try:
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
                
                print("✅ Automation complete!")
            else:
                raise Exception("登入失敗")
                
        except Exception as e:
            print(f"❌ Automation error: {e}")
            self._move_file_to_failed(xml_filepath)
            raise
    
    async def navigate_and_login(self, url: str, username: str, password: str, store_id: str = "") -> bool:
        """Navigate to CRM and login."""
        try:
            print(f"[Login] Navigating to {url}")
            await self.page.goto(url, wait_until='domcontentloaded')
            
            # Fill login form
            await self.page.fill('#Acct', username)
            await self.page.fill('#Pwd', password)
            
            # Click login button
            await self.page.click('#Send')
            print("[Login] Clicked login button")
            
            # Wait for navigation
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Check if login successful (login form should be gone)
            if await self.page.locator('#Acct').count() > 0:
                print("[Login] Failed - login form still visible")
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
        print(f"[Store] Looking for popup, store_id='{store_id}'")
        
        try:
            # Wait for popup (max 3 seconds)
            popup = self.page.locator('#switch-active-store-popup-body')
            
            try:
                await popup.wait_for(state='visible', timeout=3000)
                print("[Store] Popup found!")
            except:
                print("[Store] No popup found")
                return
            
            if store_id:
                # Select store from dropdown
                await self.page.select_option('select[name="StoreSId"]', store_id)
                print(f"[Store] Selected: {store_id}")
                
                # Click switch button
                await self.page.click('#SwitchActiveStore')
                print("[Store] Clicked switch button")
                
                # Wait for popup to close
                await popup.wait_for(state='hidden', timeout=5000)
                print("[Store] Switch complete!")
            else:
                print("[Store] No store_id, skipping")
                
        except Exception as e:
            print(f"[Store] Error: {e}")
    
    async def search_patient(self, patient_name: str, birth_date: str, timeout: int = 30) -> bool:
        """Search for patient by name and birthday."""
        try:
            print(f"[Search] Looking for: {patient_name}, DOB: {birth_date}")
            
            # Click "使用姓名+生日搜尋客戶" tab
            await self.page.click('text=使用姓名+生日搜尋客戶')
            await self.page.wait_for_timeout(500)
            
            # Fill customer name
            await self.page.fill('#Cust_Name', patient_name)
            
            # Fill birthday if provided
            if birth_date:
                parts = birth_date.split('-')
                if len(parts) == 3:
                    await self.page.fill('#CustBirthYear', parts[0])
                    await self.page.fill('#CustBirthMonth', parts[1].lstrip('0'))
                    await self.page.fill('#CustBirthDay', parts[2].lstrip('0'))
            
            # Click search button
            await self.page.click('#SearchCustNameBirth')
            print("[Search] Clicked search button")
            
            # Wait for results
            await self.page.wait_for_timeout(2000)
            
            # Find and click patient link
            patient_link = self.page.locator(f'a[title*="{patient_name}"]').first
            
            if await patient_link.count() > 0:
                await patient_link.click()
                print(f"[Search] Found and clicked: {patient_name}")
                await self.page.wait_for_load_state('networkidle')
                
                # Navigate to hearing report page
                await self._navigate_to_hearing_report()
                return True
            else:
                print(f"[Search] Patient not found: {patient_name}")
                return False
                
        except Exception as e:
            print(f"[Search] Error: {e}")
            return False
    
    async def _navigate_to_hearing_report(self):
        """Navigate to hearing report form page."""
        try:
            # Click on hearing test tab/link
            hearing_link = self.page.locator('text=聽力評估').first
            if await hearing_link.count() > 0:
                await hearing_link.click()
                await self.page.wait_for_load_state('networkidle')
                print("[Navigate] Clicked 聽力評估 link")
            else:
                # Try alternative navigation
                await self.page.click('a[href*="Hearing"]')
                await self.page.wait_for_load_state('networkidle')
                print("[Navigate] Navigated via href")
        except Exception as e:
            print(f"[Navigate] Error: {e}")
    
    async def fill_form(self, data: Dict[str, Any]):
        """Fill the hearing assessment form."""
        print(f"[Form] Filling form with {len(data)} fields")
        
        # Fill InspectorName first (required field)
        inspector_name = data.get("InspectorName", "")
        if inspector_name:
            try:
                await self.page.fill('#InspectorName', str(inspector_name))
                print(f"[Form] Filled InspectorName: {inspector_name}")
            except Exception as e:
                print(f"[Form] Error filling InspectorName: {e}")
        
        # Fill other fields from FIELD_MAP
        for field in FIELD_MAP:
            try:
                key = field.get("key")
                if not key or key not in data:
                    continue
                
                data_value = data[key]
                if data_value is None or data_value == "":
                    continue
                
                field_type = field.get("type", "input")
                selector = field.get("selector", "")
                
                if not selector:
                    continue
                
                if field_type == "input":
                    await self.page.fill(selector, str(data_value))
                elif field_type == "select":
                    await self.page.select_option(selector, str(data_value))
                elif field_type == "radio":
                    value_match = field.get("value_match")
                    if str(data_value) == str(value_match):
                        await self.page.click(selector)
                
                print(f"[Form] Filled {key}: {data_value}")
                
            except Exception as e:
                print(f"[Form] Error filling {field.get('key', '?')}: {e}")
        
        print("[Form] Form fill complete")
    
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
        """Move processed file to processed folder."""
        try:
            if not os.path.exists(PROCESSED_FOLDER):
                os.makedirs(PROCESSED_FOLDER)
            
            filename = os.path.basename(filepath)
            dest = os.path.join(PROCESSED_FOLDER, filename)
            shutil.move(filepath, dest)
            print(f"[Cleanup] Moved to processed: {filename}")
        except Exception as e:
            print(f"[Cleanup] Error moving file: {e}")
    
    def _move_file_to_failed(self, filepath: str):
        """Move failed file to failed folder."""
        try:
            if not os.path.exists(FAILED_FOLDER):
                os.makedirs(FAILED_FOLDER)
            
            filename = os.path.basename(filepath)
            dest = os.path.join(FAILED_FOLDER, filename)
            shutil.move(filepath, dest)
            print(f"[Cleanup] Moved to failed: {filename}")
        except Exception as e:
            print(f"[Cleanup] Error moving file: {e}")


# Synchronous wrapper for backward compatibility
def run_automation_sync(data_payload: Dict[str, Any], xml_filepath: str, user_config: Dict[str, str], headless: bool = True):
    """Synchronous wrapper to run automation."""
    async def _run():
        async with HearingAutomation(headless=headless) as auto:
            await auto.run_automation(data_payload, xml_filepath, user_config)
    
    asyncio.run(_run())
