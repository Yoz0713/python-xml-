import unittest
import os
import threading
import time
from selenium.webdriver.common.by import By
from src.automation import HearingAutomation
from src.parser import parse_noah_xml

class TestAutomation(unittest.TestCase):
    def test_automation_logic(self):
        # Merge parsed data with some manual data
        sessions = parse_noah_xml("tests/real_sample.xml")
        xml_data = sessions[0]

        manual_data = {
            "InspectorName": "John Doe",
            "Otoscopy_Left_Clean": "Y",
            "Otoscopy_Left_Intact": "N",
            "Otoscopy_Left_Desc": "Minor wax",
            "Otoscopy_Left_Image": os.path.abspath("tests/sample_data.xml"), # Dummy file
            "Otoscopy_Right_Clean": "N",
            "Otoscopy_Right_Intact": "Y",
            "Otoscopy_Right_Desc": "Clear",
            "Otoscopy_Right_Image": os.path.abspath("tests/sample_data.xml"), # Dummy file

            "Speech_Left_Type": "SRT",
            "Speech_Right_Type": "SDT"
        }

        full_data = {**xml_data, **manual_data}

        # Initialize automation (headless)
        automation = HearingAutomation(headless=True)
        mock_url = "file://" + os.path.abspath("tests/mock_form.html")

        # In the new logic, we don't have navigate_and_wait, we have navigate_and_login
        # And run_automation which combines everything.
        # But for testing, we might want to test components or the full run.

        # navigate_and_login expects (url, username, password)
        # It relies on specific IDs in the target page (InspectorName) or Login page.
        # Our mock_form.html has a fake login logic.

        # We need to simulate the user login again?
        # The new navigate_and_login implementation in the skeleton is:
        # def navigate_and_login(self, url, username, password, timeout=60):
        #     self.driver.get(url)
        #     time.sleep(3)
        #     # TODO: Implement robust login check
        #     return True

        # Since it just returns True after sleep, we don't need the complex threading simulation for the skeleton.
        # We just need to make sure the elements exist for fill_form.

        # However, the mock form is hidden until "login" button is clicked.
        # If the skeleton's navigate_and_login doesn't click the login button, the form fields won't be visible/interactable?
        # Actually selenium can find them if they exist in DOM, but interaction might fail if hidden.
        # The mock form has <div id="main-form" style="display:none;">

        # So we MUST make it visible.
        # Since the skeleton navigate_and_login is a placeholder, we should manually make it visible in the test
        # to verify fill_form works.

        try:
            automation.driver.get(mock_url)

            # Manually trigger the login to show the form (since skeleton doesn't do it)
            try:
                automation.driver.find_element(By.ID, "login-btn").click()
                time.sleep(1)
            except:
                pass

            # Now test fill_form
            automation.fill_form(full_data)

            # Verification: Get values from the form to verify they were filled
            driver = automation.driver

            # Check Inspector Name
            self.assertEqual(driver.find_element(By.ID, "InspectorName").get_attribute("value"), "John Doe")

            # Check Parsed Data Filling (Tymp)
            # Left Vol in real_sample is 1.63 (163/100)
            self.assertEqual(driver.find_element(By.ID, "LeftEarVol").get_attribute("value"), "1.63")

            # Check Speech
            # Left SRT in real_sample is 45.0
            self.assertEqual(driver.find_element(By.ID, "LeftSpeechThrRes").get_attribute("value"), "45.0")
            self.assertEqual(driver.find_element(By.ID, "LeftSpeechThrType").get_attribute("value"), "SRT")

        except Exception as e:
            self.fail(f"Automation failed with error: {e}")
        finally:
            automation.driver.quit()

if __name__ == "__main__":
    unittest.main()
