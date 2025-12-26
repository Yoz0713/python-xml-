import xml.etree.ElementTree as ET
from datetime import datetime

def parse_noah_xml(filepath):
    """
    Parses the NOAH XML file and extracts relevant data.

    Args:
        filepath (str): Path to the XML file.

    Returns:
        dict: A dictionary containing extracted data.
    """
    tree = ET.parse(filepath)
    root = tree.getroot()

    data = {}

    # Parse ActionDate (Test Date)
    action_date_elem = root.find("ActionDate")
    if action_date_elem is not None and action_date_elem.text:
        try:
            # Assuming format YYYY-MM-DD based on sample
            date_obj = datetime.strptime(action_date_elem.text, "%Y-%m-%d")
            data["TestDateY"] = str(date_obj.year)
            data["TestDateM"] = str(date_obj.month) # 1-12
            data["TestDateD"] = str(date_obj.day)
            data["FullTestDate"] = action_date_elem.text
        except ValueError:
            # Handle different date formats if necessary
            data["FullTestDate"] = action_date_elem.text

    # Parse Tympanometry
    tymp = root.find("Tympanometry")
    if tymp is not None:
        for side in ["Left", "Right"]:
            side_elem = tymp.find(side)
            if side_elem is not None:
                data[f"Tymp_{side}_Type"] = side_elem.findtext("Type", "")
                data[f"Tymp_{side}_Vol"] = side_elem.findtext("Volume", "")
                data[f"Tymp_{side}_Pressure"] = side_elem.findtext("Pressure", "")
                data[f"Tymp_{side}_Compliance"] = side_elem.findtext("Compliance", "")

    # Parse Speech Audiometry
    speech = root.find("SpeechAudiometry")
    if speech is not None:
        for side in ["Left", "Right"]:
            side_elem = speech.find(side)
            if side_elem is not None:
                data[f"Speech_{side}_SRT"] = side_elem.findtext("Threshold", "")
                data[f"Speech_{side}_SDS"] = side_elem.findtext("DiscriminationScore", "")
                data[f"Speech_{side}_MCL"] = side_elem.findtext("MCL", "")

    return data

if __name__ == "__main__":
    # Test with sample data
    import sys
    if len(sys.argv) > 1:
        print(parse_noah_xml(sys.argv[1]))
