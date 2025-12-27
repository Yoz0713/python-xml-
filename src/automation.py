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

            if self.navigate_and_login(url, username, password):
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

                # Submit (Placeholder - often user wants manual verification first, but batch mode implies auto)
                # self.driver.find_element(By.ID, "SubmitBtn").click()
                print("Form filled. Submitting... (Simulated)")

                # Wait for completion?
                time.sleep(2)

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

    def navigate_and_login(self, url, username, password, timeout=60):
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
                return True
                
        except Exception as e:
            print(f"Login error: {e}")
            return False

    def search_patient(self, patient_name, birth_date, timeout=30):
        """
        Search for a patient in CRM using name and birthday.
        
        Args:
            patient_name (str): Patient name (Target_Patient_Name from XML)
            birth_date (str): Birth date in YYYY-MM-DD format
            timeout (int): Wait timeout in seconds
        
        Returns:
            bool: True if search completed successfully
        """
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        try:
            wait = WebDriverWait(self.driver, timeout)
            
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
            
            # Find and click on the first matching patient in search results
            # Look for the patient name link in the table
            try:
                # Find the result table
                result_table = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".ListTable table.rwdTable")
                ))
                
                # Find all patient name links (in td.client a)
                patient_links = result_table.find_elements(By.CSS_SELECTOR, "td.client a")
                
                if patient_links:
                    # Click the first matching result
                    first_link = patient_links[0]
                    link_name = first_link.text
                    print(f"Found patient: {link_name}")
                    first_link.click()
                    
                    # Wait for patient dashboard to load
                    time.sleep(2)
                    print("Navigated to patient dashboard")
                    
                    # Now click on 聽力報告 menu
                    # TODO: Need HTML structure of the hearing report menu
                    # For now, placeholder - will be updated when user provides menu HTML
                    if not self.navigate_to_hearing_report():
                        print("Warning: Could not navigate to hearing report")
                    
                    return True
                else:
                    print("No search results found")
                    return False
                    
            except Exception as e:
                print(f"Error clicking search result: {e}")
                return False
            
        except Exception as e:
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

