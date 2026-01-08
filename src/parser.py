"""
NOAH XML Parser
Based on noah_xml_parsing_guide.md
Parses hearing assessment XML files exported from NOAH system.
"""

import xml.etree.ElementTree as ET
from datetime import datetime
import re
from typing import Optional, Dict, List, Any


def clean_xml(xml_string: str) -> str:
    """
    Remove namespace prefixes and xmlns declarations from XML.
    This simplifies ElementTree parsing significantly.
    """
    # Remove namespace prefixes: <pt:Patient> → <Patient>
    xml_string = re.sub(r'<[a-zA-Z0-9]+:([a-zA-Z0-9_\-]+)', r'<\1', xml_string)
    # Remove closing namespace prefixes: </pt:Patient> → </Patient>
    xml_string = re.sub(r'</[a-zA-Z0-9]+:([a-zA-Z0-9_\-]+)>', r'</\1>', xml_string)
    # Remove xmlns declarations
    xml_string = re.sub(r'\sxmlns[^"]+\"[^"]+\"', '', xml_string)
    xml_string = re.sub(r'\sxmlns:([a-zA-Z0-9]+)=\"[^\"]+\"', '', xml_string)
    return xml_string


def smart_clean_name(raw_first_name: str, raw_last_name: str) -> str:
    """
    Clean patient name by:
    1. Removing all digits from name strings (e.g., "10158游閔暘" -> "游閔暘")
    2. Combining in LastName + FirstName order (Chinese naming convention)
    """
    def remove_digits(text):
        if not text:
            return ""
        return re.sub(r'\d+', '', text).strip()
    
    clean_last_name = remove_digits(raw_last_name)
    clean_first_name = remove_digits(raw_first_name)
    
    # Combine in LastName + FirstName order (Chinese convention)
    name_parts = [n for n in [clean_last_name, clean_first_name] if n]
    return ''.join(name_parts)


def get_text(parent: ET.Element, tag: str) -> Optional[str]:
    """Get text content of a child tag (recursive search)"""
    node = parent.find(f'.//{tag}')
    return node.text if node is not None else None


def get_float(parent: ET.Element, tag: str) -> Optional[float]:
    """Get float value from a child tag"""
    text = get_text(parent, tag)
    if text:
        try:
            return float(text)
        except ValueError:
            return None
    return None


def classify_tympanogram_type(peak_pressure: Optional[float], peak_compliance: Optional[float]) -> str:
    """
    Classify tympanogram type based on Jerger classification.
    
    Type A:  Normal (-100 ~ +100 daPa, 0.3 ~ 1.6 mL)
    Type As: Low compliance (shallow) - compliance 0.1 ~ 0.3 mL
    Type Ad: High compliance (deep) - compliance > 1.6 mL
    Type B:  Flat (no peak) - compliance ≤ 0.1 mL
    Type C:  Negative pressure - < -100 daPa or > +100 daPa
    
    Based on noah_xml_parsing_guide.md section 5.4
    Returns only the letter/code (A, As, Ad, B, C) without "Type" prefix.
    """
    if peak_pressure is None or peak_compliance is None:
        return ""
    
    # Type B: Flat (very low compliance, no clear peak)
    if peak_compliance <= 0.1:
        return "B"
    
    # Type C: Abnormal pressure
    if peak_pressure < -100 or peak_pressure > 100:
        return "C"
    
    # Normal pressure range (-100 ~ +100 daPa), classify by compliance
    if peak_compliance < 0.3:
        return "As"  # Shallow peak
    elif peak_compliance > 1.6:
        return "Ad"  # Deep peak
    else:
        return "A"   # Normal


def get_available_sessions(filepath: str) -> Dict[str, Any]:
    """
    Parse XML and return available sessions grouped by type and date.
    Used by the wizard dialog to let user select which sessions to upload.
    
    Returns:
        {
            "patient_info": {...},
            "pta_sessions": [{"date": "2024-12-14", "display": "2024-12-14 純音聽力", ...}, ...],
            "tymp_sessions": [{"date": "2024-12-14", "display": "2024-12-14 左耳+右耳", "left": True, "right": True}, ...]
        }
    """
    # Read and clean XML
    with open(filepath, 'r', encoding='utf-8') as f:
        xml_string = f.read()
    
    cleaned_xml = clean_xml(xml_string)
    root = ET.fromstring(cleaned_xml)
    
    # Extract patient info
    raw_first_name = get_text(root, 'FirstName') or ""
    raw_last_name = get_text(root, 'LastName') or ""
    patient_name = smart_clean_name(raw_first_name, raw_last_name)
    birth_date = get_text(root, 'PatientBirthDate') or get_text(root, 'BirthDate') or ""
    if birth_date and 'T' in birth_date:
        birth_date = birth_date.split('T')[0]
    
    patient_info = {
        "Target_Patient_Name": patient_name,
        "Patient_BirthDate": birth_date,
    }
    
    # Collect session info
    pta_dates = set()
    tymp_by_date: Dict[str, Dict[str, bool]] = {}  # date -> {"left": True/False, "right": True/False}
    
    for action in root.findall('.//Action'):
        action_date_elem = action.find('ActionDate')
        if action_date_elem is None or not action_date_elem.text:
            continue
        
        full_date_str = action_date_elem.text
        date_key = full_date_str.split('T')[0]  # YYYY-MM-DD
        
        type_of_data = get_text(action, 'TypeOfData') or ""
        description = get_text(action, 'Description') or ""
        
        if 'audiogram' in type_of_data.lower():
            pta_dates.add(date_key)
        
        elif 'impedance' in type_of_data.lower():
            if date_key not in tymp_by_date:
                tymp_by_date[date_key] = {"left": False, "right": False}
            
            if 'left' in description.lower():
                tymp_by_date[date_key]["left"] = True
            elif 'right' in description.lower():
                tymp_by_date[date_key]["right"] = True
    
    # Build session lists
    pta_sessions = []
    for date in sorted(pta_dates, reverse=True):
        pta_sessions.append({
            "date": date,
            "display": f"{date} 純音聽力"
        })
    
    tymp_sessions = []
    for date in sorted(tymp_by_date.keys(), reverse=True):
        info = tymp_by_date[date]
        ears = []
        if info["left"]:
            ears.append("左耳")
        if info["right"]:
            ears.append("右耳")
        
        if ears:
            tymp_sessions.append({
                "date": date,
                "display": f"{date} {'+'.join(ears)}",
                "left": info["left"],
                "right": info["right"]
            })
    
    return {
        "patient_info": patient_info,
        "pta_sessions": pta_sessions,
        "tymp_sessions": tymp_sessions
    }

def parse_noah_xml(filepath: str) -> List[Dict[str, Any]]:
    """
    Parse NOAH XML file and extract hearing assessment data.
    
    Based on noah_xml_parsing_guide.md
    
    Args:
        filepath: Path to the XML file
        
    Returns:
        List of session dictionaries, sorted by date (newest first)
    """
    # Read and clean XML
    with open(filepath, 'r', encoding='utf-8') as f:
        xml_string = f.read()
    
    cleaned_xml = clean_xml(xml_string)
    root = ET.fromstring(cleaned_xml)
    
    # ==========================================
    # Parse Patient Info
    # ==========================================
    patient_elem = root.find('.//Patient/Patient')
    if patient_elem is None:
        patient_elem = root.find('.//Patient')
    
    raw_first_name = ""
    raw_last_name = ""
    birth_date = ""
    
    if patient_elem is not None:
        fn = patient_elem.find('FirstName')
        ln = patient_elem.find('LastName')
        # Try multiple variations for BirthDate
        dob = patient_elem.find('DateofBirth')
        if dob is None:
            dob = patient_elem.find('DateOfBirth')
        if dob is None:
            dob = patient_elem.find('BirthDate')
        
        # DEBUG: Print all children of patient element to see available tags
        print(f"[DEBUG] Patient element children: {[child.tag for child in patient_elem]}")
        if dob is not None:
             print(f"[DEBUG] Found DOB tag: {dob.tag}, text: {dob.text}")
        else:
             print("[DEBUG] DOB tag NOT FOUND")
        
        raw_first_name = fn.text if fn is not None and fn.text else ""
        raw_last_name = ln.text if ln is not None and ln.text else ""
        birth_date = dob.text if dob is not None and dob.text else ""
    
    target_patient_name = smart_clean_name(raw_first_name, raw_last_name)
    
    patient_info = {
        "Target_Patient_Name": target_patient_name,
        "Patient_BirthDate": birth_date,
        "Raw_FirstName": raw_first_name,
        "Raw_LastName": raw_last_name,
    }
    
    # ==========================================
    # Group Actions by Date
    # ==========================================
    grouped_data: Dict[str, Dict[str, Any]] = {}
    
    for action in root.findall('.//Action'):
        action_date_elem = action.find('ActionDate')
        if action_date_elem is None or not action_date_elem.text:
            continue
        
        full_date_str = action_date_elem.text
        date_key = full_date_str.split('T')[0]  # YYYY-MM-DD
        
        if date_key not in grouped_data:
            parts = date_key.split('-')
            grouped_data[date_key] = {
                "FullTestDate": full_date_str,
                "TestDateY": parts[0] if len(parts) > 0 else "",
                "TestDateM": str(int(parts[1])) if len(parts) > 1 else "",  # Remove leading zero
                "TestDateD": str(int(parts[2])) if len(parts) > 2 else "",  # Remove leading zero
            }
        
        current_session = grouped_data[date_key]
        
        type_of_data = get_text(action, 'TypeOfData') or ""
        description = get_text(action, 'Description') or ""
        
        # ==========================================
        # Parse Audiogram (Pure Tone + Speech)
        # ==========================================
        if 'audiogram' in type_of_data.lower():
            
            # --- Pure Tone Audiometry ---
            for tone_block in action.findall('.//ToneThresholdAudiogram'):
                output = get_text(tone_block, 'StimulusSignalOutput') or ""
                output_lower = output.lower()
                
                # Determine ear side
                is_right = 'right' in output_lower or output == '1'
                is_left = 'left' in output_lower or output == '2'
                side = "Right" if is_right else "Left" if is_left else None
                
                if not side:
                    continue
                
                # Determine conduction type
                is_bone = 'bone' in output_lower
                cond_type = "Bone" if is_bone else "Air"
                
                # Extract test points
                for pt_node in tone_block.findall('.//TonePoints'):
                    freq = get_float(pt_node, 'StimulusFrequency')
                    level = get_float(pt_node, 'StimulusLevel')
                    status = get_text(pt_node, 'TonePointStatus') or ""
                    
                    if freq is not None and level is not None:
                        key = f"PTA_{side}_{cond_type}_{int(freq)}"
                        # Add NR suffix if TonePointStatus is NoResponse
                        if status.lower() == 'noresponse':
                            current_session[key] = f"{int(level)}NR"
                        else:
                            current_session[key] = str(int(level))
            
            # --- UCL (Uncomfortable Level) ---
            for ucl_block in action.findall('.//UncomfortableLevel'):
                output = get_text(ucl_block, 'StimulusSignalOutput') or ""
                output_lower = output.lower()
                
                is_right = 'right' in output_lower or output == '1'
                is_left = 'left' in output_lower or output == '2'
                side = "Right" if is_right else "Left" if is_left else None
                
                if not side:
                    continue
                
                for pt_node in ucl_block.findall('.//TonePoints'):
                    freq = get_float(pt_node, 'StimulusFrequency')
                    level = get_float(pt_node, 'StimulusLevel')
                    status = get_text(pt_node, 'TonePointStatus') or ""
                    
                    if freq is not None and level is not None:
                        key = f"PTA_{side}_UCL_{int(freq)}"
                        # Add NR suffix if TonePointStatus is NoResponse
                        if status.lower() == 'noresponse':
                            current_session[key] = f"{int(level)}NR"
                        else:
                            current_session[key] = str(int(level))
            
            # --- SRT (Speech Reception Threshold) ---
            for srt_block in action.findall('.//SpeechReceptionThresholdAudiogram'):
                output = get_text(srt_block, 'StimulusSignalOutput') or ""
                
                if 'right' in output.lower():
                    side = "Right"
                elif 'left' in output.lower():
                    side = "Left"
                else:
                    continue
                
                for pt_node in srt_block.findall('.//SpeechReceptionPoints'):
                    level = get_float(pt_node, 'StimulusLevel')
                    if level is not None:
                        current_session[f"Speech_{side}_SRT"] = str(int(level))
            
            # --- SDS (Speech Discrimination Score) - take max score ---
            for sds_block in action.findall('.//SpeechDiscriminationAudiogram'):
                output = get_text(sds_block, 'StimulusSignalOutput') or ""
                
                if 'right' in output.lower():
                    side = "Right"
                elif 'left' in output.lower():
                    side = "Left"
                else:
                    continue
                
                max_score = -1
                for pt_node in sds_block.findall('.//SpeechDiscriminationPoints'):
                    score = get_float(pt_node, 'ScorePercent')
                    if score is not None and score > max_score:
                        max_score = score
                
                if max_score > -1:
                    current_session[f"Speech_{side}_SDS"] = str(int(max_score))
            
            # --- MCL (Most Comfortable Level) ---
            for mcl_block in action.findall('.//SpeechMostComfortableLevel'):
                output = get_text(mcl_block, 'StimulusSignalOutput') or ""
                
                if 'right' in output.lower():
                    side = "Right"
                elif 'left' in output.lower():
                    side = "Left"
                else:
                    continue
                
                for pt_node in mcl_block.findall('.//SpeechMostComfortablePoint'):
                    level = get_float(pt_node, 'StimulusLevel')
                    if level is not None:
                        current_session[f"Speech_{side}_MCL"] = str(int(level))
        
        # ==========================================
        # Parse Impedance (Tympanometry)
        # ==========================================
        elif 'impedance' in type_of_data.lower():
            # Determine ear side from description
            if 'right' in description.lower():
                side = "Right"
            elif 'left' in description.lower():
                side = "Left"
            else:
                continue
            
            # Find TympanogramTest block
            tymp_test = action.find('.//TympanogramTest')
            if tymp_test is not None:
                # Canal Volume (ECV)
                cv_node = tymp_test.find('.//CanalVolume')
                if cv_node is not None:
                    cv_val = get_float(cv_node, 'ArgumentCompliance1')
                    if cv_val is not None:
                        # Normalize: divide by 100 if > 5 (likely μL instead of mL)
                        if cv_val > 5:
                            cv_val = round(cv_val / 100, 2)
                        current_session[f"Tymp_{side}_Vol"] = str(cv_val)
                
                # Peak Compliance (MaximumCompliance)
                mc_node = tymp_test.find('.//MaximumCompliance')
                peak_compliance = None
                if mc_node is not None:
                    mc_val = get_float(mc_node, 'ArgumentCompliance1')
                    if mc_val is not None:
                        # Normalize: divide by 100 if > 5
                        if mc_val > 5:
                            mc_val = round(mc_val / 100, 2)
                        peak_compliance = mc_val
                        current_session[f"Tymp_{side}_Compliance"] = str(mc_val)
                
                # Peak Pressure - Find the CompliancePoint with the maximum compliance
                # The correct peak pressure is the pressure at the point of maximum compliance
                all_compliance_points = tymp_test.findall('.//CompliancePoint')
                
                if all_compliance_points:
                    max_compliance = -1
                    peak_pressure = None
                    
                    for cp in all_compliance_points:
                        pressure = get_float(cp, 'Pressure')
                        comp_node = cp.find('.//Compliance')
                        if comp_node is not None:
                            compliance = get_float(comp_node, 'ArgumentCompliance1')
                            if compliance is not None and compliance > max_compliance:
                                max_compliance = compliance
                                peak_pressure = pressure
                    
                    if peak_pressure is not None:
                        current_session[f"Tymp_{side}_Pressure"] = str(int(peak_pressure))
                else:
                    # Fallback to direct Pressure tag if no CompliancePoints
                    pressure = get_float(tymp_test, 'Pressure')
                    if pressure is not None:
                        current_session[f"Tymp_{side}_Pressure"] = str(int(pressure))
                
                # Auto-classify Type
                pressure_val = current_session.get(f"Tymp_{side}_Pressure")
                compliance_val = current_session.get(f"Tymp_{side}_Compliance")
                
                try:
                    p = float(pressure_val) if pressure_val else None
                    c = float(compliance_val) if compliance_val else None
                    tymp_type = classify_tympanogram_type(p, c)
                    if tymp_type:
                        current_session[f"Tymp_{side}_Type"] = tymp_type
                except:
                    pass
    
    # ==========================================
    # Sort by date (newest first) and add patient info
    # ==========================================
    sorted_keys = sorted(grouped_data.keys(), reverse=True)
    
    result = []
    for k in sorted_keys:
        session = grouped_data[k]
        session.update(patient_info)
        result.append(session)
    
    return result


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) > 1:
        result = parse_noah_xml(sys.argv[1])
        print(json.dumps(result, indent=2, ensure_ascii=False))
