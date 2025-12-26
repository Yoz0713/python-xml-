import unittest
import os
from selenium.webdriver.common.by import By
from src.automation import HearingAutomation
from src.parser import parse_noah_xml

class TestAutomation(unittest.TestCase):
    def test_automation_logic(self):
        # Merge parsed data with some manual data
        xml_data = parse_noah_xml("tests/sample_data.xml")

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

        # Local mock file URL
        mock_url = "file://" + os.path.abspath("tests/mock_form.html")

        try:
            # Login
            success = automation.login(mock_url, "admin", "password")
            self.assertTrue(success, "Login should succeed with mock form")

            # Fill Form
            automation.fill_form(full_data)

            # Verification: Get values from the form to verify they were filled
            # We need to access the driver directly for verification
            driver = automation.driver

            # Check Inspector Name
            self.assertEqual(driver.find_element(By.ID, "InspectorName").get_attribute("value"), "John Doe")

            # Check Date (Selects)
            self.assertEqual(driver.find_element(By.NAME, "TestDateY").get_attribute("value"), "2023")
            self.assertEqual(driver.find_element(By.NAME, "TestDateM").get_attribute("value"), "11")

            # Check Radio Buttons
            # Left Clean Y should be checked
            self.assertTrue(driver.find_element(By.ID, "LeftEarClean_Y").is_selected())
            # Left Intact N should be checked
            self.assertTrue(driver.find_element(By.ID, "LeftEarIntact_N").is_selected())

            # Check Text Area
            self.assertEqual(driver.find_element(By.ID, "LeftEarDesc").get_attribute("value"), "Minor wax")

            # Check Parsed Data Filling (Tymp)
            self.assertEqual(driver.find_element(By.ID, "LeftEarType").get_attribute("value"), "A")
            self.assertEqual(driver.find_element(By.ID, "LeftEarVol").get_attribute("value"), "0.9")

            # Check Speech
            self.assertEqual(driver.find_element(By.ID, "LeftSpeechThrRes").get_attribute("value"), "25")
            self.assertEqual(driver.find_element(By.ID, "LeftSpeechThrType").get_attribute("value"), "SRT")

        except Exception as e:
            self.fail(f"Automation failed with error: {e}")
        finally:
            automation.close()

if __name__ == "__main__":
    unittest.main()
