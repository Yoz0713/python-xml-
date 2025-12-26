import xml.etree.ElementTree as ET
from datetime import datetime

def parse_noah_xml(filepath):
    """
    Parses the NOAH XML file and extracts relevant data.
    Handles both single-session and multi-session XML structures.

    Args:
        filepath (str): Path to the XML file.

    Returns:
        list: A list of dictionaries, where each dict is a session's data.
    """
    tree = ET.parse(filepath)
    root = tree.getroot()

    sessions = []

    # Strategy: Find all elements that contain an ActionDate, treating them as session roots.
    # If the root itself has ActionDate, it's a single session.
    # If children have ActionDate, they are multiple sessions.

    potential_roots = []

    # Check root
    if root.find("ActionDate") is not None:
        potential_roots.append(root)

    # Check children (one level deep for now, or recursive if needed)
    # Using iter() to find ANY node with ActionDate is risky if nested.
    # Let's look for direct children that have ActionDate
    for child in root:
        if child.find("ActionDate") is not None:
            potential_roots.append(child)

    # If no potential roots found but root exists, maybe standard parsing failed?
    # Just return empty if really nothing.

    # De-duplicate roots (in case root matches and it's the only one)
    # logic: if root is in list, and children are too, usually implies root is a wrapper
    # but if root has ActionDate, it's usually the data.
    # Let's assume if children have ActionDate, we ignore root's ActionDate if it's just metadata?
    # Or just process all unique elements.

    unique_roots = list(set(potential_roots))
    # Sort by something? Document order.

    if not unique_roots:
        # Fallback: maybe just try to parse root even if ActionDate missing?
        # But for now, require ActionDate
        pass

    for session_root in unique_roots:
        data = {}

        # Parse ActionDate (Test Date)
        action_date_elem = session_root.find("ActionDate")
        if action_date_elem is not None and action_date_elem.text:
            try:
                # Assuming format YYYY-MM-DD based on sample
                date_obj = datetime.strptime(action_date_elem.text, "%Y-%m-%d")
                data["TestDateY"] = str(date_obj.year)
                data["TestDateM"] = str(date_obj.month) # 1-12
                data["TestDateD"] = str(date_obj.day)
                data["FullTestDate"] = action_date_elem.text
            except ValueError:
                data["FullTestDate"] = action_date_elem.text
        else:
            data["FullTestDate"] = "Unknown Date"

        # Parse Tympanometry
        tymp = session_root.find("Tympanometry")
        if tymp is not None:
            for side in ["Left", "Right"]:
                side_elem = tymp.find(side)
                if side_elem is not None:
                    data[f"Tymp_{side}_Type"] = side_elem.findtext("Type", "")
                    data[f"Tymp_{side}_Vol"] = side_elem.findtext("Volume", "")
                    data[f"Tymp_{side}_Pressure"] = side_elem.findtext("Pressure", "")
                    data[f"Tymp_{side}_Compliance"] = side_elem.findtext("Compliance", "")

        # Parse Speech Audiometry
        speech = session_root.find("SpeechAudiometry")
        if speech is not None:
            for side in ["Left", "Right"]:
                side_elem = speech.find(side)
                if side_elem is not None:
                    data[f"Speech_{side}_SRT"] = side_elem.findtext("Threshold", "")
                    data[f"Speech_{side}_SDS"] = side_elem.findtext("DiscriminationScore", "")
                    data[f"Speech_{side}_MCL"] = side_elem.findtext("MCL", "")

        sessions.append(data)

    return sessions

if __name__ == "__main__":
    # Test with sample data
    import sys
    if len(sys.argv) > 1:
        print(parse_noah_xml(sys.argv[1]))
