import unittest
import os
from src.parser import parse_noah_xml

class TestParser(unittest.TestCase):
    def test_parse_sample(self):
        filepath = "tests/sample_data.xml"
        data = parse_noah_xml(filepath)

        self.assertEqual(data["TestDateY"], "2023")
        self.assertEqual(data["TestDateM"], "11")
        self.assertEqual(data["TestDateD"], "15")

        self.assertEqual(data["Tymp_Left_Type"], "A")
        self.assertEqual(data["Tymp_Left_Vol"], "0.9")
        self.assertEqual(data["Tymp_Left_Pressure"], "-10")
        self.assertEqual(data["Tymp_Left_Compliance"], "0.5")

        self.assertEqual(data["Tymp_Right_Type"], "B")
        self.assertEqual(data["Tymp_Right_Vol"], "1.1")

        self.assertEqual(data["Speech_Left_SRT"], "25")
        self.assertEqual(data["Speech_Left_SDS"], "95")
        self.assertEqual(data["Speech_Left_MCL"], "55")

if __name__ == "__main__":
    unittest.main()
