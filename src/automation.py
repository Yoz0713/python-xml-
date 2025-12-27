import time
import os
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from src.config import FIELD_MAP, PROCESSED_FOLDER, FAILED_FOLDER

# Placeholder imports for Google Sheets
# import gspread
# from oauth2client.service_account import ServiceAccountCredentials

class HearingAutomation:
    def __init__(self, headless=False):
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        # Basic anti-detection
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"Error using webdriver_manager: {e}. Falling back to default.")
            self.driver = webdriver.Chrome(options=options)

    def run_automation(self, data_payload, xml_filepath=None, user_config=None):
        """
        Shared Automation Logic.
        data_payload: Dictionary containing all merged data (XML + Manual Defaults).
        xml_filepath: Path to the source file (for cleanup).
        user_config: Dict with url, username, password.
        """
        try:
            # 1. Google Sheets Logic (Placeholder)
            self._google_sheets_check(data_payload)

            # 2. CRM Automation
            url = user_config.get("url")
            username = user_config.get("username")
            password = user_config.get("password")
            store_id = user_config.get("store_id", "")

            if self.navigate_and_login(url, username, password, store_id=store_id):
                # Search Patient using name and DOB from XML
                patient_name = data_payload.get("Target_Patient_Name", "")
                birth_date = data_payload.get("Patient_BirthDate", "")
                
                if patient_name:
                    if not self.search_patient(patient_name, birth_date):
                        raise Exception(f"無法找到病患: {patient_name}")
                
                # Duplicate Check (Placeholder)
                # if self._check_duplicate_date(data_payload["TestDate"]):
                #    raise Exception("Duplicate Date Found")

                # Fill Form
                self.fill_form(data_payload)

                # Submit the form
                # Button: <button type="button" id="Send"><span>確認送出</span></button>
                submit_btn = self.driver.find_element(By.CSS_SELECTOR, ".submit button#Send")
                submit_btn.click()
                print("Form submitted!")

                # Wait for submission to complete
                time.sleep(3)

                # 3. Cleanup
                if xml_filepath:
                    self._move_file(xml_filepath, "success")

            else:
                raise Exception("Failed to reach target page.")

        except Exception as e:
            print(f"Automation Failed: {e}")
            if xml_filepath:
                self._move_file(xml_filepath, "failure")
            raise e
        finally:
            self.driver.quit()

    def navigate_and_login(self, url, username, password, timeout=60, store_id=""):
        """Navigate to CRM and perform login with provided credentials."""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        self.driver.get(url)
        
        try:
            # Wait for login form to appear
            wait = WebDriverWait(self.driver, timeout)
            
            # Find and fill username (工號)
            acct_field = wait.until(EC.presence_of_element_located((By.ID, "Acct")))
            acct_field.clear()
            acct_field.send_keys(username)
            
            # Find and fill password (密碼)
            pwd_field = self.driver.find_element(By.ID, "Pwd")
            pwd_field.clear()
            pwd_field.send_keys(password)
            
            # Click login button (員工登入)
            send_btn = self.driver.find_element(By.ID, "Send")
            send_btn.click()
            
            # Wait for login to complete (wait for login form to disappear or new page element)
            time.sleep(3)
            
            # Check if login was successful (login form should no longer be present)
            try:
                self.driver.find_element(By.ID, "Acct")
                # If we can still find the login form, login might have failed
                print("Warning: Login form still present, login may have failed")
                return False
            except NoSuchElementException:
                # Login form gone = success
                print("Login successful")
                
                # Handle store switch popup (切換店別) if it appears
                self._handle_store_popup(store_id)
                
                return True
            
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def _handle_store_popup(self, store_id=""):
        """Handle the store switch popup - either switch store or dismiss it."""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        try:
            time.sleep(2)  # Wait for popup to appear (increased from 1s)
            
            # Check if popup exists
            popup = self.driver.find_elements(By.ID, "store-switch")
            if not popup or not popup[0].is_displayed():
                print("No store switch popup found")
                return
            
            print(f"Store popup found. store_id to switch: '{store_id}'")
            
            # If store_id is provided, switch to that store
            if store_id:
                # Select the store from dropdown
                store_select = Select(self.driver.find_element(By.NAME, "StoreSId"))
                store_select.select_by_value(store_id)
                print(f"Selected store: {store_id}")
                
                # Click the switch button
                switch_btn = self.driver.find_element(By.ID, "SwitchActiveStore")
                switch_btn.click()
                print("Clicked switch store button - waiting for page reload...")
                
                # Wait for page to reload after store switch (wait for popup to disappear)
                time.sleep(5)  # Give page time to reload
                
                # Wait until popup is gone or page is reloaded
                try:
                    wait = WebDriverWait(self.driver, 10)
                    wait.until(EC.invisibility_of_element_located((By.ID, "store-switch")))
                    print("Store switch complete - popup closed")
                except:
                    print("Store switch - popup may still be visible, continuing anyway")
                
            else:
                # Just close the popup without switching
                close_link = self.driver.find_element(By.CSS_SELECTOR, "#store-switch span.close a")
                close_link.click()
                print("Closed store switch popup (no switch)")
                time.sleep(1)
            
        except Exception as e:
            print(f"Popup handling error: {e}")

    def search_patient(self, patient_name, birth_date, timeout=30):
        """
        Search for a patient in CRM using name and birthday.
        Raises exception if multiple patients with same name+birthday found.
        
        Args:
            patient_name (str): Patient name (Target_Patient_Name from XML)
            birth_date (str): Birth date in YYYY-MM-DD format
            timeout (int): Wait timeout in seconds
        
        Returns:
            bool: True if search completed successfully
            
        Raises:
            Exception: If multiple patients found (duplicate detection)
        """
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        try:
            wait = WebDriverWait(self.driver, timeout)
            
            # First, switch to "使用姓名+生日搜尋客戶" tab (it's the second li element)
            try:
                name_birthday_tab = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//ul/li[2]/a[contains(.//span, '使用姓名') or contains(.//span, '生日')]")
                ))
                name_birthday_tab.click()
                print("Switched to Name+Birthday search mode")
                time.sleep(1)
            except Exception as e:
                print(f"Could not find search mode tabs, trying direct: {e}")
            
            # Wait for search form to be available
            name_field = wait.until(EC.presence_of_element_located((By.NAME, "QName")))
            
            # Fill in patient name
            name_field.clear()
            name_field.send_keys(patient_name)
            print(f"Filled patient name: {patient_name}")
            
            # Parse and fill birthday if available
            if birth_date:
                try:
                    # Parse YYYY-MM-DD format
                    parts = birth_date.split('-')
                    if len(parts) == 3:
                        year, month, day = parts
                        
                        # Select Year (QBirthdayY)
                        year_select = Select(self.driver.find_element(By.NAME, "QBirthdayY"))
                        year_select.select_by_value(year)
                        
                        # Select Month (QBirthdayM) - remove leading zero
                        month_select = Select(self.driver.find_element(By.NAME, "QBirthdayM"))
                        month_select.select_by_value(str(int(month)))
                        
                        # Wait for day options to populate (some forms dynamically load days)
                        time.sleep(0.5)
                        
                        # Select Day (QBirthdayD) - remove leading zero
                        day_select = Select(self.driver.find_element(By.NAME, "QBirthdayD"))
                        day_select.select_by_value(str(int(day)))
                        
                        print(f"Filled birthday: {year}/{month}/{day}")
                except Exception as e:
                    print(f"Warning: Could not fill birthday: {e}")
            
            # Click search button
            search_btn = self.driver.find_element(By.NAME, "SearchByPerson")
            search_btn.click()
            print("Clicked search button")
            
            # Wait for search results to load
            time.sleep(2)
            
            # Find and check search results
            try:
                # Find the result table
                result_table = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".ListTable table.rwdTable")
                ))
                
                # Find all patient name links (in td.client a)
                patient_links = result_table.find_elements(By.CSS_SELECTOR, "td.client a")
                
                if len(patient_links) == 0:
                    raise Exception(f"找不到病患: {patient_name}")
                
                elif len(patient_links) > 1:
                    # DUPLICATE DETECTION - Multiple patients found
                    found_names = [link.text for link in patient_links[:5]]  # Get first 5 names
                    raise Exception(f"重複病患警告: 找到 {len(patient_links)} 位相同姓名或條件的病患: {', '.join(found_names)}")
                
                else:
                    # Exactly one patient found - proceed
                    first_link = patient_links[0]
                    link_name = first_link.text
                    print(f"Found unique patient: {link_name}")
                    first_link.click()
                    
                    # Wait for patient dashboard to load
                    time.sleep(2)
                    print("Navigated to patient dashboard")
                    
                    # Now click on 聽力報告 menu
                    if not self.navigate_to_hearing_report():
                        print("Warning: Could not navigate to hearing report")
                    
                    return True
                
            except Exception as e:
                if "重複病患" in str(e) or "找不到病患" in str(e):
                    raise  # Re-raise duplicate/not-found errors
                print(f"Error clicking search result: {e}")
                return False
            
        except Exception as e:
            if "重複病患" in str(e) or "找不到病患" in str(e):
                raise  # Re-raise duplicate/not-found errors
            print(f"Search error: {e}")
            return False

    def navigate_to_hearing_report(self, timeout=30):
        """
        Navigate to the hearing report form from patient dashboard.
        Two-step process: 聽力報告 menu → 新增聽力報告 button
        
        Returns:
            bool: True if navigation successful
        """
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        try:
            wait = WebDriverWait(self.driver, timeout)
            
            # Step 1: Click 聽力報告 in the navigation menu
            # Look for link containing "聽力報告" in the nav_list
            hearing_menu = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".nav_list a[href*='czhearingreport']")
            ))
            hearing_menu.click()
            print("Clicked 聽力報告 menu")
            
            # Wait for hearing report list page to load
            time.sleep(2)
            
            # Step 2: Click 新增聽力報告 button
            add_report_btn = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "a.add_hearing_rep")
            ))
            add_report_btn.click()
            print("Clicked 新增聽力報告 button")
            
            # Wait for form to load
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"Error navigating to hearing report: {e}")
            return False

    def fill_form(self, data):
        """Iterates through FIELD_MAP and fills the form."""
        # Debug: Print key fields
        print(f"=== Fill Form Debug ===")
        print(f"InspectorName: '{data.get('InspectorName', 'NOT FOUND')}'")
        print(f"TestDateY: '{data.get('TestDateY', 'NOT FOUND')}'")
        print(f"========================")
        
        # CRITICAL: Fill InspectorName first (required field)
        inspector_name = data.get("InspectorName", "")
        if inspector_name:
            try:
                inspector_field = self.driver.find_element(By.ID, "InspectorName")
                inspector_field.clear()
                inspector_field.send_keys(str(inspector_name))
                print(f"Filled InspectorName: {inspector_name}")
            except Exception as e:
                print(f"Error filling InspectorName: {e}")
        else:
            print("WARNING: InspectorName is empty!")
        
        for field in FIELD_MAP:
            try:
                # Determine value to input
                key = field.get("key")
                val_match = field.get("value_match") # For radio buttons

                if not key or key not in data:
                    continue

                data_value = data[key]

                # Selector
                by = By.ID
                if field["selector_type"] == "Name": by = By.NAME
                elif field["selector_type"] == "Class": by = By.CLASS_NAME

                selector = field["selector_value"]
                input_type = field["input_type"]

                element = self.driver.find_element(by, selector)

                if input_type == "Text" or input_type == "Textarea":
                    element.clear()
                    element.send_keys(str(data_value))

                elif input_type == "Select":
                    Select(element).select_by_value(str(data_value))

                elif input_type == "Radio":
                    # Only click if data_value matches the value_match for this radio button
                    if str(data_value) == str(val_match):
                        element.click()

                elif input_type == "File":
                    if data_value and os.path.exists(data_value):
                        element.send_keys(data_value)

            except NoSuchElementException:
                # print(f"Skipping {field['name']}: Element not found.")
                pass
            except Exception as e:
                print(f"Error on {field['name']}: {e}")

    def _google_sheets_check(self, data):
        # TODO: Connect to Google Sheets
        # TODO: Check for duplicates
        # TODO: Append row if new
        print("Google Sheets Check (Placeholder)")
        pass

    def _move_file(self, filepath, status):
        """Moves file to Processed or Failed folder."""
        if not filepath: return

        directory = os.path.dirname(filepath)
        filename = os.path.basename(filepath)

        target_dir = os.path.join(directory, PROCESSED_FOLDER if status == "success" else FAILED_FOLDER)
        os.makedirs(target_dir, exist_ok=True)

        destination = os.path.join(target_dir, filename)

        # Handle duplicate filenames
        if os.path.exists(destination):
            base, ext = os.path.splitext(filename)
            destination = os.path.join(target_dir, f"{base}_{int(time.time())}{ext}")

        try:
            shutil.move(filepath, destination)
            print(f"Moved {filename} to {target_dir}")
        except Exception as e:
            print(f"Failed to move file: {e}")

