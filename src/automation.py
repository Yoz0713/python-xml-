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
                # Search Patient (Placeholder)
                # self._search_patient(data_payload["PatientID"])

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
        self.driver.get(url)
        # Skeleton logic same as before, condensed
        # ... (Login detection and handling)
        # For skeleton, assume success or simple check
        time.sleep(3)
        # TODO: Implement robust login check
        return True

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

