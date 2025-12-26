import unittest
import os
from src.parser import parse_noah_xml

class TestParser(unittest.TestCase):
    def test_parse_real_sample(self):
        filepath = "tests/real_sample.xml"
        sessions = parse_noah_xml(filepath)

        self.assertTrue(len(sessions) > 0, "Should extract at least one session")
        data = sessions[0]

        # Check Date Extraction
        self.assertEqual(data["TestDateY"], "2025")
        self.assertEqual(data["TestDateM"], "12")
        self.assertEqual(data["TestDateD"], "15")

        # Check Speech Extraction (Right)
        # XML: SRT 20.0, SDS 96.00, MCL 55.0
        self.assertEqual(data.get("Speech_Right_SRT"), "20.0")
        self.assertEqual(data.get("Speech_Right_SDS"), "96.00")
        self.assertEqual(data.get("Speech_Right_MCL"), "55.0")

        # Check Speech Extraction (Left)
        # XML: SRT 45.0, SDS 76.00, MCL 80.0
        self.assertEqual(data.get("Speech_Left_SRT"), "45.0")
        self.assertEqual(data.get("Speech_Left_SDS"), "76.00")
        self.assertEqual(data.get("Speech_Left_MCL"), "80.0")

        # Check Tymp Extraction (Right)
        # XML: Vol 188 -> 1.88, Comp 111 -> 1.11, Pressure -10
        self.assertEqual(data.get("Tymp_Right_Vol"), "1.88")
        self.assertEqual(data.get("Tymp_Right_Compliance"), "1.11")
        self.assertEqual(data.get("Tymp_Right_Pressure"), "-10")

        # Check Tymp Extraction (Left)
        # XML: Vol 163 -> 1.63, Comp 50 -> 0.5, Pressure -10
        self.assertEqual(data.get("Tymp_Left_Vol"), "1.63")
        self.assertEqual(data.get("Tymp_Left_Compliance"), "0.5")
        self.assertEqual(data.get("Tymp_Left_Pressure"), "-10")

if __name__ == "__main__":
    unittest.main()
