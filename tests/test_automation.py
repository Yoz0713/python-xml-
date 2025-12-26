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
        # The mock form has the "InspectorName" field inside the "main-form" div
        # But initially "main-form" is hidden.
        # However, our automation waits for "InspectorName".
        # In the mock HTML, "InspectorName" exists but is inside a display:none div.
        # Selenium's presence_of_element_located detects it even if hidden?
        # No, usually we want visibility or just existence.
        # But wait, the mock form has a LOGIN form first.
        # Our new logic waits for "InspectorName".
        # So in the test, we need to simulate the user logging in.

        # Actually, for testing, we can just point to a mock page where InspectorName is already present.
        # OR we can modify the test to interact with the login form "manually" to simulate the user.

        mock_url = "file://" + os.path.abspath("tests/mock_form.html")

        # Start the automation in a thread or just call logic?
        # We need to simulate the user action while navigate_and_wait is running.
        # But navigate_and_wait is blocking.
        # So we can't do that easily in a single-threaded test without threading.

        # Ideally, we modify the mock form so that InspectorName is present immediately
        # OR we just test that it works when it IS present.

        # Let's assume for this test we update the mock form or just 'login' manually before calling navigate_and_wait?
        # No, navigate_and_wait does the `get`.

        # Simpler approach for unit test:
        # Just update mock_form.html to have InspectorName visible immediately?
        # Or better: Use a thread in the test to click the login button after a delay.

        import threading
        import time
        from selenium.webdriver.common.by import By

        def simulate_user_login(driver):
            time.sleep(2)
            try:
                # Click the mock login button
                driver.find_element(By.ID, "login-btn").click()
            except:
                pass

        try:
            # We can't pass the driver to the thread easily before it's created,
            # but we can access it from the automation object.

            # Launch the waiter
            # But wait, navigate_and_wait blocks until success.
            # So we need the simulator to run in parallel.

            t = threading.Thread(target=simulate_user_login, args=(automation.driver,))
            # However, automation.driver is initialized.
            # navigate_and_wait calls get(url).

            # We need to start the simulation thread AFTER get(url) is called but BEFORE it returns?
            # That's tricky because navigate_and_wait does both.

            # Use a slightly modified approach for test:
            # We can trust that WebDriverWait works.
            # Let's just use a mock page where it IS present for verification of fill_form.
            # And maybe a separate test for the wait logic.

            # Let's stick to the current plan:
            # The current mock form requires clicking login.
            # Let's spawn the thread before calling navigate.

            t.start()

            # Navigate and Wait (this will block until InspectorName is found)
            # The thread will click the button which makes InspectorName visible.
            success = automation.navigate_and_wait(mock_url, timeout=10)
            self.assertTrue(success, "Should detect target page after manual login")

            t.join()

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
