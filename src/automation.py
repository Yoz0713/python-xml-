import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException

class HearingAutomation:
    def __init__(self, headless=False):
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # In a real app, we might want to manage the driver path more robustly
        # using webdriver_manager, but for now we rely on installed drivers or system path.
        # For the sandbox, I assume chromedriver is available.
        # However, to be safe and cross-platform friendly for the user:
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"Error using webdriver_manager: {e}. Falling back to default.")
            self.driver = webdriver.Chrome(options=options)

    def navigate_and_wait(self, url, username=None, password=None, timeout=300):
        """
        Navigates to the URL and waits for the user to be logged in
        (if necessary) by checking for a key form element.
        Handles redirection to Login page and back to Target if needed.
        """
        self.driver.get(url)

        target_element_id = "InspectorName"
        login_input_id = "Acct" # Based on user feedback

        start_time = time.time()

        while time.time() - start_time < timeout:
            # 1. Check if we are on Target Page
            try:
                self.driver.find_element(By.ID, target_element_id)
                print("Target page detected.")
                return True
            except NoSuchElementException:
                pass

            # 2. Check if we are on Login Page
            try:
                acct_input = self.driver.find_element(By.ID, login_input_id)
                print("Login page detected.")

                # If we have credentials, try to auto-login
                if username and password:
                    try:
                        pwd_input = self.driver.find_element(By.ID, "Pwd")
                        send_btn = self.driver.find_element(By.ID, "Send")

                        # Only fill if empty to avoid fighting with user?
                        # Or just fill.
                        if not acct_input.get_attribute("value"):
                            acct_input.send_keys(username)
                            pwd_input.send_keys(password)
                            send_btn.click()
                            print("Auto-login attempted.")
                            time.sleep(2) # Wait for transition

                            # After login, system might redirect to Home, not Target.
                            # So we might need to navigate to URL again.
                            # But let's check current URL or Page Title first?
                            # Simplest: just wait a bit and if not on target, re-navigate.
                    except Exception as e:
                        print(f"Auto-login error: {e}")
            except NoSuchElementException:
                pass

            # 3. Check if we are logged in but on Home/Dashboard (not Target)
            # This is tricky without knowing Home page ID.
            # But if we are NOT on Login and NOT on Target, and we just logged in...
            # We should try to re-navigate to target_url.

            # Heuristic: If we are not on Login Page and not on Target Page,
            # and it's been a few seconds since start, maybe we need to force reload target url?
            # Or assume user is navigating.

            # User specific complaint: "Redirects to Home".
            # So if we detect we are NOT on Login page anymore, but still not on Target...
            # Re-issue get(url).

            # To avoid infinite reload loops, let's only do this if we think we are logged in.
            # If Login ID is missing, we assume logged in.

            try:
                self.driver.find_element(By.ID, login_input_id)
                is_login_page = True
            except NoSuchElementException:
                is_login_page = False

            if not is_login_page:
                # potentially logged in
                try:
                    self.driver.find_element(By.ID, target_element_id)
                    return True
                except NoSuchElementException:
                    # Not on target, not on login. Likely Home.
                    # Re-navigate to target url
                    # throttle this
                    print("Not on target or login. Re-navigating to target URL...")
                    self.driver.get(url)
                    time.sleep(3) # Wait for load

            time.sleep(1)

        print("Timeout waiting for target page.")
        return False

    def fill_form(self, data):
        """
        Fills the form based on the mapped data.
        Args:
            data (dict): Dictionary where keys correspond to the 'name' in mapping
                         and values are the values to fill.
                         (Merged XML and Manual data)
        """
        # Mapping definition from Prompt Part 2
        mapping = [
            {"category": "Basic", "name": "InspectorName", "selector_type": "ID", "selector_value": "InspectorName", "input_type": "Text"},
            {"category": "Basic", "name": "TestDateY", "selector_type": "Name", "selector_value": "TestDateY", "input_type": "Select"},
            {"category": "Basic", "name": "TestDateM", "selector_type": "Name", "selector_value": "TestDateM", "input_type": "Select"},
            {"category": "Basic", "name": "TestDateD", "selector_type": "Name", "selector_value": "TestDateD", "input_type": "Select"},

            {"category": "Otoscopy_Left", "name": "Clean_Y", "selector_type": "ID", "selector_value": "LeftEarClean_Y", "input_type": "Radio"},
            {"category": "Otoscopy_Left", "name": "Clean_N", "selector_type": "ID", "selector_value": "LeftEarClean_N", "input_type": "Radio"},
            {"category": "Otoscopy_Left", "name": "Intact_Y", "selector_type": "ID", "selector_value": "LeftEarIntact_Y", "input_type": "Radio"},
            {"category": "Otoscopy_Left", "name": "Intact_N", "selector_type": "ID", "selector_value": "LeftEarIntact_N", "input_type": "Radio"},
            {"category": "Otoscopy_Left", "name": "Image", "selector_type": "Class", "selector_value": "dev-upload-left-otoscopic", "input_type": "File"},
            {"category": "Otoscopy_Left", "name": "Desc", "selector_type": "ID", "selector_value": "LeftEarDesc", "input_type": "Textarea"},

            {"category": "Otoscopy_Right", "name": "Clean_Y", "selector_type": "ID", "selector_value": "RightEarClean_Y", "input_type": "Radio"},
            {"category": "Otoscopy_Right", "name": "Clean_N", "selector_type": "ID", "selector_value": "RightEarClean_N", "input_type": "Radio"},
            {"category": "Otoscopy_Right", "name": "Intact_Y", "selector_type": "ID", "selector_value": "RightEarIntact_Y", "input_type": "Radio"},
            {"category": "Otoscopy_Right", "name": "Intact_N", "selector_type": "ID", "selector_value": "RightEarIntact_N", "input_type": "Radio"},
            {"category": "Otoscopy_Right", "name": "Image", "selector_type": "Class", "selector_value": "dev-upload-right-otoscopic", "input_type": "File"},
            {"category": "Otoscopy_Right", "name": "Desc", "selector_type": "ID", "selector_value": "RightEarDesc", "input_type": "Textarea"},

            {"category": "Tymp_Left", "name": "Type", "key": "Tymp_Left_Type", "selector_type": "ID", "selector_value": "LeftEarType", "input_type": "Text"},
            {"category": "Tymp_Left", "name": "Vol", "key": "Tymp_Left_Vol", "selector_type": "ID", "selector_value": "LeftEarVol", "input_type": "Text"},
            {"category": "Tymp_Left", "name": "Pressure", "key": "Tymp_Left_Pressure", "selector_type": "ID", "selector_value": "LeftEarPressure", "input_type": "Text"},
            {"category": "Tymp_Left", "name": "Compliance", "key": "Tymp_Left_Compliance", "selector_type": "ID", "selector_value": "LeftEarCompliance", "input_type": "Text"},

            {"category": "Tymp_Right", "name": "Type", "key": "Tymp_Right_Type", "selector_type": "ID", "selector_value": "RightEarType", "input_type": "Text"},
            {"category": "Tymp_Right", "name": "Vol", "key": "Tymp_Right_Vol", "selector_type": "ID", "selector_value": "RightEarVol", "input_type": "Text"},
            {"category": "Tymp_Right", "name": "Pressure", "key": "Tymp_Right_Pressure", "selector_type": "ID", "selector_value": "RightEarPressure", "input_type": "Text"},
            {"category": "Tymp_Right", "name": "Compliance", "key": "Tymp_Right_Compliance", "selector_type": "ID", "selector_value": "RightEarCompliance", "input_type": "Text"},

            {"category": "Speech_Left", "name": "Type", "key": "Speech_Left_Type", "selector_type": "ID", "selector_value": "LeftSpeechThrType", "input_type": "Select"},
            {"category": "Speech_Left", "name": "SRT", "key": "Speech_Left_SRT", "selector_type": "ID", "selector_value": "LeftSpeechThrRes", "input_type": "Text"},
            {"category": "Speech_Left", "name": "SDS", "key": "Speech_Left_SDS", "selector_type": "ID", "selector_value": "LeftSpeechScore", "input_type": "Text"},
            {"category": "Speech_Left", "name": "MCL", "key": "Speech_Left_MCL", "selector_type": "ID", "selector_value": "LeftSpeechMcl", "input_type": "Text"},

            {"category": "Speech_Right", "name": "Type", "key": "Speech_Right_Type", "selector_type": "ID", "selector_value": "RightSpeechThrType", "input_type": "Select"},
            {"category": "Speech_Right", "name": "SRT", "key": "Speech_Right_SRT", "selector_type": "ID", "selector_value": "RightSpeechThrRes", "input_type": "Text"},
            {"category": "Speech_Right", "name": "SDS", "key": "Speech_Right_SDS", "selector_type": "ID", "selector_value": "RightSpeechScore", "input_type": "Text"},
            {"category": "Speech_Right", "name": "MCL", "key": "Speech_Right_MCL", "selector_type": "ID", "selector_value": "RightSpeechMcl", "input_type": "Text"}
        ]

        # Note: I added "key" to some fields above to match my parser output keys.
        # For others (like Radio buttons), the logic is slightly different.
        # The data dict keys need to match what the GUI/Parser produces.

        # Let's normalize the data access.
        # The `data` dict keys will be like:
        # InspectorName, TestDateY, TestDateM, TestDateD
        # Otoscopy_Left_Clean ('Y' or 'N'), Otoscopy_Left_Intact ('Y' or 'N'), Otoscopy_Left_Desc, Otoscopy_Left_Image
        # Tymp_Left_Type, ...
        # Speech_Left_Type, Speech_Left_SRT, ...

        for field in mapping:
            # Determine the key to look up in `data`
            key = field.get("key")
            if not key:
                # Construct key based on category and name if not explicit
                # Otoscopy_Left + Clean_Y is not a direct key.
                # The data will likely have "Otoscopy_Left_Clean" = "Y"
                pass

            # Selector Strategy
            by = By.ID
            if field["selector_type"] == "Name":
                by = By.NAME
            elif field["selector_type"] == "Class":
                by = By.CLASS_NAME

            val = field["selector_value"]

            try:
                element = self.driver.find_element(by, val)
                input_type = field["input_type"]

                # Logic for values
                # We need to map the Field Name to the Data Key
                # Example: Field "InspectorName" -> Data "InspectorName"
                # Example: Field "Clean_Y" (Radio) -> check if Data "Otoscopy_Left_Clean" == "Y"

                # Construct expected data key logic
                data_value = None
                should_interact = False

                if field["category"] == "Basic":
                    data_value = data.get(field["name"]) # e.g. InspectorName, TestDateY
                    if data_value: should_interact = True

                elif "Otoscopy" in field["category"]:
                    side = "Left" if "Left" in field["category"] else "Right"
                    if "Clean" in field["name"]:
                        # e.g. Clean_Y. Check if data[Otoscopy_{side}_Clean] == Y (from suffix)
                        target_val = field["name"].split("_")[1] # Y or N
                        actual_val = data.get(f"Otoscopy_{side}_Clean")
                        if actual_val == target_val:
                            should_interact = True

                    elif "Intact" in field["name"]:
                        target_val = field["name"].split("_")[1]
                        actual_val = data.get(f"Otoscopy_{side}_Intact")
                        if actual_val == target_val:
                            should_interact = True

                    elif field["name"] == "Desc":
                        data_value = data.get(f"Otoscopy_{side}_Desc")
                        if data_value: should_interact = True

                    elif field["name"] == "Image":
                        data_value = data.get(f"Otoscopy_{side}_Image")
                        if data_value: should_interact = True

                elif "Tymp" in field["category"] or "Speech" in field["category"]:
                    # These use the keys I added to the mapping list or inferred
                    # e.g. Tymp_Left_Type
                    if key and key in data:
                        data_value = data[key]
                        should_interact = True

                # Perform Interaction
                if should_interact:
                    if input_type == "Text" or input_type == "Textarea":
                        element.clear()
                        element.send_keys(str(data_value))
                    elif input_type == "Select":
                        Select(element).select_by_value(str(data_value))
                    elif input_type == "Radio":
                        element.click()
                    elif input_type == "File":
                        element.send_keys(str(data_value)) # Send path

            except NoSuchElementException:
                print(f"Element not found: {field['selector_value']} (Category: {field['category']}, Name: {field['name']})")
            except Exception as e:
                print(f"Error interacting with {field['selector_value']}: {e}")

    def close(self):
        self.driver.quit()
