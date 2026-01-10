# ==========================================
# USER CONFIGURATION SECTION
# ==========================================
import sys
import os

def get_base_path():
    """Get the base path for resources."""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe - use executable location
        return os.path.dirname(sys.executable)
    else:
        # Running as script - use project root (parent of src)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_PATH = get_base_path()
CRM_URL = "https://crm.greattree.com.tw/..."  # Placeholder
GOOGLE_JSON_PATH = os.path.join(BASE_PATH, "service_account.json")
GOOGLE_SHEET_NAME = "Hearing_Assessment_Log"

# Folders for file management
PROCESSED_FOLDER = "Processed"
FAILED_FOLDER = "Failed"

# ==========================================
# FIELD MAPPING - CRM Hearing Report Form
# ==========================================
# Maps XML data keys to CRM HTML form elements

FIELD_MAP = [
    # ==========================================
    # 基本設定 (Basic Settings)
    # ==========================================
    {"name": "檢查人員姓名", "selector_type": "ID", "selector_value": "InspectorName", "input_type": "Text", "key": "InspectorName"},
    {"name": "施測日期(年)", "selector_type": "Name", "selector_value": "TestDateY", "input_type": "Select", "key": "TestDateY"},
    {"name": "施測日期(月)", "selector_type": "Name", "selector_value": "TestDateM", "input_type": "Select", "key": "TestDateM"},
    {"name": "施測日期(日)", "selector_type": "Name", "selector_value": "TestDateD", "input_type": "Select", "key": "TestDateD"},

    # ==========================================
    # 耳鏡檢查 - 左耳 (Otoscopy - Left)
    # ==========================================
    {"name": "左耳耳道乾淨(是)", "selector_type": "ID", "selector_value": "LeftEarClean_Y", "input_type": "Radio", "key": "Otoscopy_Left_Clean", "value_match": "True"},
    {"name": "左耳耳道乾淨(否)", "selector_type": "ID", "selector_value": "LeftEarClean_N", "input_type": "Radio", "key": "Otoscopy_Left_Clean", "value_match": "False"},
    {"name": "左耳鼓膜完整(是)", "selector_type": "ID", "selector_value": "LeftEarIntact_Y", "input_type": "Radio", "key": "Otoscopy_Left_Intact", "value_match": "True"},
    {"name": "左耳鼓膜完整(否)", "selector_type": "ID", "selector_value": "LeftEarIntact_N", "input_type": "Radio", "key": "Otoscopy_Left_Intact", "value_match": "False"},
    {"name": "左耳耳鏡圖", "selector_type": "Class", "selector_value": "dev-upload-left-otoscopic", "input_type": "File", "key": "Otoscopy_Left_Image"},
    {"name": "左耳其他說明", "selector_type": "ID", "selector_value": "LeftEarDesc", "input_type": "Textarea", "key": "Otoscopy_Left_Desc"},

    # ==========================================
    # 耳鏡檢查 - 右耳 (Otoscopy - Right)
    # ==========================================
    {"name": "右耳耳道乾淨(是)", "selector_type": "ID", "selector_value": "RightEarClean_Y", "input_type": "Radio", "key": "Otoscopy_Right_Clean", "value_match": "True"},
    {"name": "右耳耳道乾淨(否)", "selector_type": "ID", "selector_value": "RightEarClean_N", "input_type": "Radio", "key": "Otoscopy_Right_Clean", "value_match": "False"},
    {"name": "右耳鼓膜完整(是)", "selector_type": "ID", "selector_value": "RightEarIntact_Y", "input_type": "Radio", "key": "Otoscopy_Right_Intact", "value_match": "True"},
    {"name": "右耳鼓膜完整(否)", "selector_type": "ID", "selector_value": "RightEarIntact_N", "input_type": "Radio", "key": "Otoscopy_Right_Intact", "value_match": "False"},
    {"name": "右耳耳鏡圖", "selector_type": "Class", "selector_value": "dev-upload-right-otoscopic", "input_type": "File", "key": "Otoscopy_Right_Image"},
    {"name": "右耳其他說明", "selector_type": "ID", "selector_value": "RightEarDesc", "input_type": "Textarea", "key": "Otoscopy_Right_Desc"},

    # ==========================================
    # 中耳鼓室圖 - 左耳 (Tympanometry - Left)
    # ==========================================
    {"name": "左耳類型", "selector_type": "ID", "selector_value": "LeftEarType", "input_type": "Text", "key": "Tymp_Left_Type"},
    {"name": "左耳耳道容積", "selector_type": "ID", "selector_value": "LeftEarVol", "input_type": "Text", "key": "Tymp_Left_Vol"},
    {"name": "左耳峰值壓力", "selector_type": "ID", "selector_value": "LeftEarPressure", "input_type": "Text", "key": "Tymp_Left_Pressure"},
    {"name": "左耳峰值聲導抗", "selector_type": "ID", "selector_value": "LeftEarCompliance", "input_type": "Text", "key": "Tymp_Left_Compliance"},

    # ==========================================
    # 中耳鼓室圖 - 右耳 (Tympanometry - Right)
    # ==========================================
    {"name": "右耳類型", "selector_type": "ID", "selector_value": "RightEarType", "input_type": "Text", "key": "Tymp_Right_Type"},
    {"name": "右耳耳道容積", "selector_type": "ID", "selector_value": "RightEarVol", "input_type": "Text", "key": "Tymp_Right_Vol"},
    {"name": "右耳峰值壓力", "selector_type": "ID", "selector_value": "RightEarPressure", "input_type": "Text", "key": "Tymp_Right_Pressure"},
    {"name": "右耳峰值聲導抗", "selector_type": "ID", "selector_value": "RightEarCompliance", "input_type": "Text", "key": "Tymp_Right_Compliance"},

    # ==========================================
    # 純音聽力檢查 - 左耳氣導 (Pure Tone - Left Air)
    # ==========================================
    {"name": "左耳氣導250Hz", "selector_type": "ID", "selector_value": "LeftAir250hz", "input_type": "Text", "key": "PTA_Left_Air_250"},
    {"name": "左耳氣導500Hz", "selector_type": "ID", "selector_value": "LeftAir500hz", "input_type": "Text", "key": "PTA_Left_Air_500"},
    {"name": "左耳氣導750Hz", "selector_type": "ID", "selector_value": "LeftAir750hz", "input_type": "Text", "key": "PTA_Left_Air_750"},
    {"name": "左耳氣導1000Hz", "selector_type": "ID", "selector_value": "LeftAir1000hz", "input_type": "Text", "key": "PTA_Left_Air_1000"},
    {"name": "左耳氣導1500Hz", "selector_type": "ID", "selector_value": "LeftAir1500hz", "input_type": "Text", "key": "PTA_Left_Air_1500"},
    {"name": "左耳氣導2000Hz", "selector_type": "ID", "selector_value": "LeftAir2000hz", "input_type": "Text", "key": "PTA_Left_Air_2000"},
    {"name": "左耳氣導3000Hz", "selector_type": "ID", "selector_value": "LeftAir3000hz", "input_type": "Text", "key": "PTA_Left_Air_3000"},
    {"name": "左耳氣導4000Hz", "selector_type": "ID", "selector_value": "LeftAir4000hz", "input_type": "Text", "key": "PTA_Left_Air_4000"},
    {"name": "左耳氣導6000Hz", "selector_type": "ID", "selector_value": "LeftAir6000hz", "input_type": "Text", "key": "PTA_Left_Air_6000"},
    {"name": "左耳氣導8000Hz", "selector_type": "ID", "selector_value": "LeftAir8000hz", "input_type": "Text", "key": "PTA_Left_Air_8000"},

    # ==========================================
    # 純音聽力檢查 - 左耳骨導 (Pure Tone - Left Bone)
    # ==========================================
    {"name": "左耳骨導500Hz", "selector_type": "ID", "selector_value": "LeftBone500hz", "input_type": "Text", "key": "PTA_Left_Bone_500"},
    {"name": "左耳骨導1000Hz", "selector_type": "ID", "selector_value": "LeftBone1000hz", "input_type": "Text", "key": "PTA_Left_Bone_1000"},
    {"name": "左耳骨導2000Hz", "selector_type": "ID", "selector_value": "LeftBone2000hz", "input_type": "Text", "key": "PTA_Left_Bone_2000"},
    {"name": "左耳骨導4000Hz", "selector_type": "ID", "selector_value": "LeftBone4000hz", "input_type": "Text", "key": "PTA_Left_Bone_4000"},

    # ==========================================
    # 純音聽力檢查 - 左耳UCL (Pure Tone - Left UCL)
    # ==========================================
    {"name": "左耳UCL 250Hz", "selector_type": "ID", "selector_value": "LeftUcl250hz", "input_type": "Text", "key": "PTA_Left_UCL_250"},
    {"name": "左耳UCL 500Hz", "selector_type": "ID", "selector_value": "LeftUcl500hz", "input_type": "Text", "key": "PTA_Left_UCL_500"},
    {"name": "左耳UCL 750Hz", "selector_type": "ID", "selector_value": "LeftUcl750hz", "input_type": "Text", "key": "PTA_Left_UCL_750"},
    {"name": "左耳UCL 1000Hz", "selector_type": "ID", "selector_value": "LeftUcl1000hz", "input_type": "Text", "key": "PTA_Left_UCL_1000"},
    {"name": "左耳UCL 1500Hz", "selector_type": "ID", "selector_value": "LeftUcl1500hz", "input_type": "Text", "key": "PTA_Left_UCL_1500"},
    {"name": "左耳UCL 2000Hz", "selector_type": "ID", "selector_value": "LeftUcl2000hz", "input_type": "Text", "key": "PTA_Left_UCL_2000"},
    {"name": "左耳UCL 3000Hz", "selector_type": "ID", "selector_value": "LeftUcl3000hz", "input_type": "Text", "key": "PTA_Left_UCL_3000"},
    {"name": "左耳UCL 4000Hz", "selector_type": "ID", "selector_value": "LeftUcl4000hz", "input_type": "Text", "key": "PTA_Left_UCL_4000"},
    {"name": "左耳UCL 6000Hz", "selector_type": "ID", "selector_value": "LeftUcl6000hz", "input_type": "Text", "key": "PTA_Left_UCL_6000"},
    {"name": "左耳UCL 8000Hz", "selector_type": "ID", "selector_value": "LeftUcl8000hz", "input_type": "Text", "key": "PTA_Left_UCL_8000"},

    # ==========================================
    # 純音聽力檢查 - 右耳氣導 (Pure Tone - Right Air)
    # ==========================================
    {"name": "右耳氣導250Hz", "selector_type": "ID", "selector_value": "RightAir250hz", "input_type": "Text", "key": "PTA_Right_Air_250"},
    {"name": "右耳氣導500Hz", "selector_type": "ID", "selector_value": "RightAir500hz", "input_type": "Text", "key": "PTA_Right_Air_500"},
    {"name": "右耳氣導750Hz", "selector_type": "ID", "selector_value": "RightAir750hz", "input_type": "Text", "key": "PTA_Right_Air_750"},
    {"name": "右耳氣導1000Hz", "selector_type": "ID", "selector_value": "RightAir1000hz", "input_type": "Text", "key": "PTA_Right_Air_1000"},
    {"name": "右耳氣導1500Hz", "selector_type": "ID", "selector_value": "RightAir1500hz", "input_type": "Text", "key": "PTA_Right_Air_1500"},
    {"name": "右耳氣導2000Hz", "selector_type": "ID", "selector_value": "RightAir2000hz", "input_type": "Text", "key": "PTA_Right_Air_2000"},
    {"name": "右耳氣導3000Hz", "selector_type": "ID", "selector_value": "RightAir3000hz", "input_type": "Text", "key": "PTA_Right_Air_3000"},
    {"name": "右耳氣導4000Hz", "selector_type": "ID", "selector_value": "RightAir4000hz", "input_type": "Text", "key": "PTA_Right_Air_4000"},
    {"name": "右耳氣導6000Hz", "selector_type": "ID", "selector_value": "RightAir6000hz", "input_type": "Text", "key": "PTA_Right_Air_6000"},
    {"name": "右耳氣導8000Hz", "selector_type": "ID", "selector_value": "RightAir8000hz", "input_type": "Text", "key": "PTA_Right_Air_8000"},

    # ==========================================
    # 純音聽力檢查 - 右耳骨導 (Pure Tone - Right Bone)
    # ==========================================
    {"name": "右耳骨導500Hz", "selector_type": "ID", "selector_value": "RightBone500hz", "input_type": "Text", "key": "PTA_Right_Bone_500"},
    {"name": "右耳骨導1000Hz", "selector_type": "ID", "selector_value": "RightBone1000hz", "input_type": "Text", "key": "PTA_Right_Bone_1000"},
    {"name": "右耳骨導2000Hz", "selector_type": "ID", "selector_value": "RightBone2000hz", "input_type": "Text", "key": "PTA_Right_Bone_2000"},
    {"name": "右耳骨導4000Hz", "selector_type": "ID", "selector_value": "RightBone4000hz", "input_type": "Text", "key": "PTA_Right_Bone_4000"},

    # ==========================================
    # 純音聽力檢查 - 右耳UCL (Pure Tone - Right UCL)
    # ==========================================
    {"name": "右耳UCL 250Hz", "selector_type": "ID", "selector_value": "RightUcl250hz", "input_type": "Text", "key": "PTA_Right_UCL_250"},
    {"name": "右耳UCL 500Hz", "selector_type": "ID", "selector_value": "RightUcl500hz", "input_type": "Text", "key": "PTA_Right_UCL_500"},
    {"name": "右耳UCL 750Hz", "selector_type": "ID", "selector_value": "RightUcl750hz", "input_type": "Text", "key": "PTA_Right_UCL_750"},
    {"name": "右耳UCL 1000Hz", "selector_type": "ID", "selector_value": "RightUcl1000hz", "input_type": "Text", "key": "PTA_Right_UCL_1000"},
    {"name": "右耳UCL 1500Hz", "selector_type": "ID", "selector_value": "RightUcl1500hz", "input_type": "Text", "key": "PTA_Right_UCL_1500"},
    {"name": "右耳UCL 2000Hz", "selector_type": "ID", "selector_value": "RightUcl2000hz", "input_type": "Text", "key": "PTA_Right_UCL_2000"},
    {"name": "右耳UCL 3000Hz", "selector_type": "ID", "selector_value": "RightUcl3000hz", "input_type": "Text", "key": "PTA_Right_UCL_3000"},
    {"name": "右耳UCL 4000Hz", "selector_type": "ID", "selector_value": "RightUcl4000hz", "input_type": "Text", "key": "PTA_Right_UCL_4000"},
    {"name": "右耳UCL 6000Hz", "selector_type": "ID", "selector_value": "RightUcl6000hz", "input_type": "Text", "key": "PTA_Right_UCL_6000"},
    {"name": "右耳UCL 8000Hz", "selector_type": "ID", "selector_value": "RightUcl8000hz", "input_type": "Text", "key": "PTA_Right_UCL_8000"},

    # ==========================================
    # 言語聽力檢查 - 左耳 (Speech Audiometry - Left)
    # ==========================================
    {"name": "左耳言語項目", "selector_type": "ID", "selector_value": "LeftSpeechThrType", "input_type": "Select", "key": "Speech_Left_Type"},
    {"name": "左耳語音閾值", "selector_type": "ID", "selector_value": "LeftSpeechThrRes", "input_type": "Text", "key": "Speech_Left_SRT"},
    {"name": "左耳語音辨識分數", "selector_type": "ID", "selector_value": "LeftSpeechScore", "input_type": "Text", "key": "Speech_Left_SDS"},
    {"name": "左耳語音舒適響度", "selector_type": "ID", "selector_value": "LeftSpeechMcl", "input_type": "Text", "key": "Speech_Left_MCL"},

    # ==========================================
    # 言語聽力檢查 - 右耳 (Speech Audiometry - Right)
    # ==========================================
    {"name": "右耳言語項目", "selector_type": "ID", "selector_value": "RightSpeechThrType", "input_type": "Select", "key": "Speech_Right_Type"},
    {"name": "右耳語音閾值", "selector_type": "ID", "selector_value": "RightSpeechThrRes", "input_type": "Text", "key": "Speech_Right_SRT"},
    {"name": "右耳語音辨識分數", "selector_type": "ID", "selector_value": "RightSpeechScore", "input_type": "Text", "key": "Speech_Right_SDS"},
    {"name": "右耳語音舒適響度", "selector_type": "ID", "selector_value": "RightSpeechMcl", "input_type": "Text", "key": "Speech_Right_MCL"},

    # ==========================================
    # 中耳聽反射 - 左耳同側 (Acoustic Reflex - Left Ipsi)
    # ==========================================
    {"name": "左耳同側聽反射500Hz", "selector_type": "ID", "selector_value": "LeftReflex500hz", "input_type": "Text", "key": "Reflex_Left_Ipsi_500"},
    {"name": "左耳同側聽反射1000Hz", "selector_type": "ID", "selector_value": "LeftReflex1000hz", "input_type": "Text", "key": "Reflex_Left_Ipsi_1000"},
    {"name": "左耳同側聽反射2000Hz", "selector_type": "ID", "selector_value": "LeftReflex2000hz", "input_type": "Text", "key": "Reflex_Left_Ipsi_2000"},

    # ==========================================
    # 中耳聽反射 - 左耳對側 (Acoustic Reflex - Left Contra)
    # ==========================================
    {"name": "左耳對側聽反射500Hz", "selector_type": "ID", "selector_value": "LeftCrossReflex500hz", "input_type": "Text", "key": "Reflex_Left_Contra_500"},
    {"name": "左耳對側聽反射1000Hz", "selector_type": "ID", "selector_value": "LeftCrossReflex1000hz", "input_type": "Text", "key": "Reflex_Left_Contra_1000"},
    {"name": "左耳對側聽反射2000Hz", "selector_type": "ID", "selector_value": "LeftCrossReflex2000hz", "input_type": "Text", "key": "Reflex_Left_Contra_2000"},

    # ==========================================
    # 中耳聽反射 - 右耳同側 (Acoustic Reflex - Right Ipsi)
    # ==========================================
    {"name": "右耳同側聽反射500Hz", "selector_type": "ID", "selector_value": "RightReflex500hz", "input_type": "Text", "key": "Reflex_Right_Ipsi_500"},
    {"name": "右耳同側聽反射1000Hz", "selector_type": "ID", "selector_value": "RightReflex1000hz", "input_type": "Text", "key": "Reflex_Right_Ipsi_1000"},
    {"name": "右耳同側聽反射2000Hz", "selector_type": "ID", "selector_value": "RightReflex2000hz", "input_type": "Text", "key": "Reflex_Right_Ipsi_2000"},

    # ==========================================
    # 中耳聽反射 - 右耳對側 (Acoustic Reflex - Right Contra)
    # ==========================================
    {"name": "右耳對側聽反射500Hz", "selector_type": "ID", "selector_value": "RightCrossReflex500hz", "input_type": "Text", "key": "Reflex_Right_Contra_500"},
    {"name": "右耳對側聽反射1000Hz", "selector_type": "ID", "selector_value": "RightCrossReflex1000hz", "input_type": "Text", "key": "Reflex_Right_Contra_1000"},
    {"name": "右耳對側聽反射2000Hz", "selector_type": "ID", "selector_value": "RightCrossReflex2000hz", "input_type": "Text", "key": "Reflex_Right_Contra_2000"},
]
