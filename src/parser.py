import xml.etree.ElementTree as ET
from datetime import datetime
import re

def smart_clean_name(raw_first_name, raw_last_name):
    """
    Clean patient name by:
    1. Removing all digits from name strings (e.g., "10158游閔暘" -> "游閔暘")
    2. Combining in LastName + FirstName order (Chinese naming convention)
    
    Args:
        raw_first_name (str): Raw first name from XML
        raw_last_name (str): Raw last name from XML
    
    Returns:
        str: Cleaned patient name (LastName + FirstName, digits removed)
    """
    def remove_digits(text):
        """Remove all digit characters from a string"""
        if not text:
            return ""
        return re.sub(r'\d+', '', text).strip()
    
    # Clean both names by removing digits
    clean_last_name = remove_digits(raw_last_name)
    clean_first_name = remove_digits(raw_first_name)
    
    # Combine in LastName + FirstName order (Chinese convention)
    # Filter out empty strings
    name_parts = [n for n in [clean_last_name, clean_first_name] if n]
    
    return ''.join(name_parts)


def classify_tympanogram_type(pressure, compliance):
    """
    Automatically classify tympanogram type based on pressure and compliance values.
    
    Classification criteria:
    - Type A: Normal (-100 to +50 daPa, compliance 0.3-1.75 ml)
    - Type As: Low compliance (shallow) - compliance < 0.3 ml
    - Type Ad: High compliance (deep) - compliance > 1.75 ml
    - Type B: Flat (no clear peak, or abnormal values)
    - Type C: Negative pressure (< -100 daPa with normal compliance)
    
    Args:
        pressure (str/float): Peak pressure in daPa
        compliance (str/float): Peak compliance in ml
    
    Returns:
        str: Tympanogram type (A, As, Ad, B, or C)
    """
    try:
        p = float(pressure) if pressure else None
        c = float(compliance) if compliance else None
        
        if p is None or c is None:
            return ""  # Can't classify without data
        
        # Type B: Very low/no compliance (flat tympanogram)
        if c < 0.1:
            return "B"
        
        # Type C: Significant negative pressure with normal compliance
        if p < -100 and 0.3 <= c <= 1.75:
            return "C"
        
        # Normal pressure range (-100 to +50)
        if -100 <= p <= 50:
            if c < 0.3:
                return "As"  # Low compliance
            elif c > 1.75:
                return "Ad"  # High compliance
            else:
                return "A"   # Normal
        
        # Outside normal pressure range but has compliance
        if c >= 0.3:
            if p < -100:
                return "C"
            else:
                return "A"  # Positive pressure, rare
        
        return "B"  # Default to B if unclear
        
    except (ValueError, TypeError):
        return ""  # Can't parse values

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

    # =========================================
    # Extract Patient Info (Name, DOB)
    # =========================================
    patient_elem = root.find('.//pt:Patient/pt:Patient', ns)
    if patient_elem is None:
        patient_elem = root.find('.//pt:Patient', ns)
    
    raw_first_name = ""
    raw_last_name = ""
    birth_date = ""
    
    if patient_elem is not None:
        first_name_elem = patient_elem.find('pt:FirstName', ns)
        last_name_elem = patient_elem.find('pt:LastName', ns)
        dob_elem = patient_elem.find('pt:DateofBirth', ns)
        
        if first_name_elem is not None and first_name_elem.text:
            raw_first_name = first_name_elem.text
        if last_name_elem is not None and last_name_elem.text:
            raw_last_name = last_name_elem.text
        if dob_elem is not None and dob_elem.text:
            birth_date = dob_elem.text
    
    # Apply Smart Name Cleaning
    target_patient_name = smart_clean_name(raw_first_name, raw_last_name)
    
    # Patient info to be added to each session
    patient_info = {
        "Target_Patient_Name": target_patient_name,
        "Patient_BirthDate": birth_date,
        "Raw_FirstName": raw_first_name,
        "Raw_LastName": raw_last_name,
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

                    # ==========================================
                    # Pure Tone Audiometry - Air & Bone Conduction
                    # ==========================================
                    elif "ToneThresholdAudiogram" in clean_tag:
                        # Determine Air or Bone conduction from StimulusSignalOutput
                        conduction_type = "Air"  # Default
                        if conditions is not None:
                            output = conditions.find('aud:StimulusSignalOutput', ns)
                            if output is not None and output.text:
                                if "BoneConductor" in output.text:
                                    conduction_type = "Bone"
                                elif "AirConductor" in output.text:
                                    conduction_type = "Air"
                        
                        # Extract all TonePoints
                        tone_points = child.findall('.//aud:TonePoints', ns)
                        for point in tone_points:
                            freq_elem = point.find('aud:StimulusFrequency', ns)
                            level_elem = point.find('aud:StimulusLevel', ns)
                            if freq_elem is not None and level_elem is not None:
                                freq = freq_elem.text
                                level = level_elem.text
                                # Create key like PTA_Left_Air_500 or PTA_Right_Bone_1000
                                current_session[f"PTA_{side}_{conduction_type}_{freq}"] = level

                    # ==========================================
                    # Uncomfortable Level (UCL)
                    # ==========================================
                    elif "UncomfortableLevel" in clean_tag:
                        # Extract all TonePoints for UCL
                        tone_points = child.findall('.//aud:TonePoints', ns)
                        for point in tone_points:
                            freq_elem = point.find('aud:StimulusFrequency', ns)
                            level_elem = point.find('aud:StimulusLevel', ns)
                            if freq_elem is not None and level_elem is not None:
                                freq = freq_elem.text
                                level = level_elem.text
                                # Create key like PTA_Left_UCL_500
                                current_session[f"PTA_{side}_UCL_{freq}"] = level

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

                    # Auto-classify tympanogram type based on pressure and compliance
                    pressure_val = current_session.get(f"Tymp_{side}_Pressure")
                    compliance_val = current_session.get(f"Tymp_{side}_Compliance")
                    tymp_type = classify_tympanogram_type(pressure_val, compliance_val)
                    if tymp_type:
                        current_session[f"Tymp_{side}_Type"] = tymp_type

    # Convert dictionary values to list, sorted by date (reverse?)
    # Sort keys decending
    sorted_keys = sorted(grouped_data.keys(), reverse=True)
    
    # Add patient info to each session
    result = []
    for k in sorted_keys:
        session = grouped_data[k]
        session.update(patient_info)  # Add Target_Patient_Name, Patient_BirthDate, etc.
        result.append(session)

    return result

if __name__ == "__main__":
    # Test with sample data
    import sys
    if len(sys.argv) > 1:
        print(parse_noah_xml(sys.argv[1]))
