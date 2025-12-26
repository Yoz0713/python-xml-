import xml.etree.ElementTree as ET
from datetime import datetime

def parse_noah_xml(filepath):
    """
    Parses the NOAH XML file and extracts relevant data.
    Handles both single-session and multi-session XML structures.
    Uses namespaces to navigate the complex NOAH structure.

    Args:
        filepath (str): Path to the XML file.

    Returns:
        list: A list of dictionaries, where each dict is a merged session's data.
    """
    tree = ET.parse(filepath)
    root = tree.getroot()

    # Namespaces
    # pt is defined in the root
    ns = {
        'pt': 'http://www.himsa.com/Measurement/PatientExport.xsd',
        'aud': 'http://www.himsa.com/Measurement/Audiogram',
        'imp': 'http://www.himsa.com/Measurement/Impedance'
    }

    # Group actions by Date (YYYY-MM-DD)
    grouped_data = {}

    # Find all actions
    actions = root.findall('.//pt:Action', ns)

    for action in actions:
        action_date_elem = action.find('pt:ActionDate', ns)
        if action_date_elem is None or not action_date_elem.text:
            continue

        full_date_str = action_date_elem.text
        # Extract YYYY-MM-DD for grouping
        try:
            date_key = full_date_str.split('T')[0]
        except:
            date_key = full_date_str

        if date_key not in grouped_data:
            grouped_data[date_key] = {
                "FullTestDate": full_date_str, # Keep first encountered timestamp or just date
                "TestDateY": date_key.split('-')[0],
                "TestDateM": date_key.split('-')[1],
                "TestDateD": date_key.split('-')[2],
            }

        current_session = grouped_data[date_key]
        type_of_data = action.find('pt:TypeOfData', ns).text
        description = action.find('pt:Description', ns).text or ""

        public_data = action.find('pt:PublicData', ns)
        if public_data is None:
            continue

        # Parse Audiogram (Speech)
        if type_of_data == "Audiogram":
            # Finding Speech Data
            # Note: The xmlns inside PublicData/HIMSAAudiometricStandard is often the default or 'aud'
            # But ElementTree might handle it as default namespace if not prefixed.
            # We can use wildcard or specific namespace.

            # Let's try to find HIMSAAudiometricStandard
            standard = public_data.find('.//aud:HIMSAAudiometricStandard', ns)
            if standard is None:
                # Fallback: try without namespace or wildcard
                standard = public_data.find('.//{http://www.himsa.com/Measurement/Audiogram}HIMSAAudiometricStandard')

            if standard is not None:
                # Iterate over children to find speech tests
                for child in standard:
                    tag = child.tag
                    # Remove namespace for easier checking
                    clean_tag = tag.split('}')[-1] if '}' in tag else tag

                    # Determine Ear
                    conditions = child.find('.//aud:AudMeasurementConditions', ns)
                    side = "Unknown"
                    if conditions is not None:
                        output = conditions.find('aud:StimulusSignalOutput', ns)
                        if output is not None and output.text:
                            if "Right" in output.text:
                                side = "Right"
                            elif "Left" in output.text:
                                side = "Left"

                    if side == "Unknown":
                        continue

                    # Extract Data
                    if "SpeechReceptionThresholdAudiogram" in clean_tag:
                        points = child.find('.//aud:SpeechReceptionPoints', ns)
                        if points is not None:
                            val = points.find('aud:StimulusLevel', ns)
                            if val is not None:
                                current_session[f"Speech_{side}_SRT"] = val.text

                    elif "SpeechDiscriminationAudiogram" in clean_tag:
                        points = child.find('.//aud:SpeechDiscriminationPoints', ns)
                        if points is not None:
                            val = points.find('aud:ScorePercent', ns)
                            if val is not None:
                                current_session[f"Speech_{side}_SDS"] = val.text

                    elif "SpeechMostComfortableLevel" in clean_tag:
                        points = child.find('.//aud:SpeechMostComfortablePoint', ns)
                        if points is not None:
                            val = points.find('aud:StimulusLevel', ns)
                            if val is not None:
                                current_session[f"Speech_{side}_MCL"] = val.text

        # Parse Impedance (Tymp)
        elif "Impedance" in type_of_data:
            # Determine Side from Description usually: "Tympanometry Right"
            side = "Unknown"
            if "Right" in description:
                side = "Right"
            elif "Left" in description:
                side = "Left"

            if side == "Unknown":
                continue

            # Parse Data
            # Namespace inside is imp
            impedance_measure = public_data.find('.//imp:AcousticImpedanceCompleteMeasurement', ns)
            if impedance_measure is not None:
                tymp_test = impedance_measure.find('.//imp:TympanogramTest', ns)
                if tymp_test is not None:
                    # Pressure
                    pressure = tymp_test.find('imp:Pressure', ns)
                    if pressure is not None:
                        current_session[f"Tymp_{side}_Pressure"] = pressure.text

                    # Volume (CanalVolume)
                    # Structure: CanalVolume -> ComplianceValue -> ArgumentCompliance1
                    vol_container = tymp_test.find('imp:CanalVolume', ns)
                    if vol_container is not None:
                        val = vol_container.find('.//imp:ArgumentCompliance1', ns)
                        if val is not None:
                            # Convert 188 -> 1.88?
                            # If value > 10, likely needs scaling.
                            # User sample had 0.9. Real xml has 188.
                            # Safest is to just provide raw or naive scale.
                            # Let's try scaling by 100 if > 100? Or just divide by 100.
                            # 1.88ml is reasonable. 188ml is impossible.
                            try:
                                v_float = float(val.text)
                                if v_float > 10:
                                    current_session[f"Tymp_{side}_Vol"] = str(v_float / 100)
                                else:
                                    current_session[f"Tymp_{side}_Vol"] = val.text
                            except:
                                current_session[f"Tymp_{side}_Vol"] = val.text

                    # Compliance (MaximumCompliance)
                    comp_container = tymp_test.find('imp:MaximumCompliance', ns)
                    if comp_container is not None:
                        val = comp_container.find('.//imp:ArgumentCompliance1', ns)
                        if val is not None:
                            # 111 -> 1.11?
                            try:
                                v_float = float(val.text)
                                if v_float > 10:
                                    current_session[f"Tymp_{side}_Compliance"] = str(v_float / 100)
                                else:
                                    current_session[f"Tymp_{side}_Compliance"] = val.text
                            except:
                                current_session[f"Tymp_{side}_Compliance"] = val.text

                    # Type? Not in XML explicitly.
                    # Leave blank or default?
                    # current_session[f"Tymp_{side}_Type"] = ""

    # Convert dictionary values to list, sorted by date (reverse?)
    # Sort keys decending
    sorted_keys = sorted(grouped_data.keys(), reverse=True)
    result = [grouped_data[k] for k in sorted_keys]

    return result

if __name__ == "__main__":
    # Test with sample data
    import sys
    if len(sys.argv) > 1:
        print(parse_noah_xml(sys.argv[1]))
