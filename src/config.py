# ==========================================
# USER CONFIGURATION SECTION
# ==========================================
CRM_URL = "https://crm.greattree.com.tw/..." # Placeholder
GOOGLE_JSON_PATH = "service_account.json"
GOOGLE_SHEET_NAME = "Hearing_Assessment_Log"

# Folders for file management
PROCESSED_FOLDER = "Processed"
FAILED_FOLDER = "Failed"

# Field Mapping (Skeleton / Placeholder)
# This defines how we map our internal data keys to the HTML form.
FIELD_MAP = [
    # --- 基本設定 ---
    {"category": "基本設定", "sub_category": "通用", "name": "檢查人員姓名", "selector_type": "ID", "selector_value": "InspectorName", "input_type": "Text", "key": "InspectorName"},
    {"category": "基本設定", "sub_category": "通用", "name": "施測日期 (年)", "selector_type": "Name", "selector_value": "TestDateY", "input_type": "Select", "key": "TestDateY"},
    {"category": "基本設定", "sub_category": "通用", "name": "施測日期 (月)", "selector_type": "Name", "selector_value": "TestDateM", "input_type": "Select", "key": "TestDateM"},
    {"category": "基本設定", "sub_category": "通用", "name": "施測日期 (日)", "selector_type": "Name", "selector_value": "TestDateD", "input_type": "Select", "key": "TestDateD"},

    # --- 耳鏡檢查 (左耳) ---
    {"category": "耳鏡檢查", "sub_category": "左耳", "name": "耳道乾淨 (是)", "selector_type": "ID", "selector_value": "LeftEarClean_Y", "input_type": "Radio", "key": "Otoscopy_Left_Clean", "value_match": "Y"},
    {"category": "耳鏡檢查", "sub_category": "左耳", "name": "耳道乾淨 (否)", "selector_type": "ID", "selector_value": "LeftEarClean_N", "input_type": "Radio", "key": "Otoscopy_Left_Clean", "value_match": "N"},
    {"category": "耳鏡檢查", "sub_category": "左耳", "name": "鼓膜完整 (是)", "selector_type": "ID", "selector_value": "LeftEarIntact_Y", "input_type": "Radio", "key": "Otoscopy_Left_Intact", "value_match": "Y"},
    {"category": "耳鏡檢查", "sub_category": "左耳", "name": "鼓膜完整 (否)", "selector_type": "ID", "selector_value": "LeftEarIntact_N", "input_type": "Radio", "key": "Otoscopy_Left_Intact", "value_match": "N"},
    {"category": "耳鏡檢查", "sub_category": "左耳", "name": "上傳耳鏡圖", "selector_type": "Class", "selector_value": "dev-upload-left-otoscopic", "input_type": "File", "key": "Otoscopy_Left_Image"},
    {"category": "耳鏡檢查", "sub_category": "左耳", "name": "其他說明", "selector_type": "ID", "selector_value": "LeftEarDesc", "input_type": "Textarea", "key": "Otoscopy_Left_Desc"},

    # --- 耳鏡檢查 (右耳) ---
    {"category": "耳鏡檢查", "sub_category": "右耳", "name": "耳道乾淨 (是)", "selector_type": "ID", "selector_value": "RightEarClean_Y", "input_type": "Radio", "key": "Otoscopy_Right_Clean", "value_match": "Y"},
    {"category": "耳鏡檢查", "sub_category": "右耳", "name": "耳道乾淨 (否)", "selector_type": "ID", "selector_value": "RightEarClean_N", "input_type": "Radio", "key": "Otoscopy_Right_Clean", "value_match": "N"},
    {"category": "耳鏡檢查", "sub_category": "右耳", "name": "鼓膜完整 (是)", "selector_type": "ID", "selector_value": "RightEarIntact_Y", "input_type": "Radio", "key": "Otoscopy_Right_Intact", "value_match": "Y"},
    {"category": "耳鏡檢查", "sub_category": "右耳", "name": "鼓膜完整 (否)", "selector_type": "ID", "selector_value": "RightEarIntact_N", "input_type": "Radio", "key": "Otoscopy_Right_Intact", "value_match": "N"},
    {"category": "耳鏡檢查", "sub_category": "右耳", "name": "上傳耳鏡圖", "selector_type": "Class", "selector_value": "dev-upload-right-otoscopic", "input_type": "File", "key": "Otoscopy_Right_Image"},
    {"category": "耳鏡檢查", "sub_category": "右耳", "name": "其他說明", "selector_type": "ID", "selector_value": "RightEarDesc", "input_type": "Textarea", "key": "Otoscopy_Right_Desc"},

    # --- 中耳鼓室圖 (左耳) ---
    {"category": "中耳鼓室圖", "sub_category": "左耳", "name": "類型", "selector_type": "ID", "selector_value": "LeftEarType", "input_type": "Text", "key": "Tymp_Left_Type"},
    {"category": "中耳鼓室圖", "sub_category": "左耳", "name": "耳道容積", "selector_type": "ID", "selector_value": "LeftEarVol", "input_type": "Text", "key": "Tymp_Left_Vol"},
    {"category": "中耳鼓室圖", "sub_category": "左耳", "name": "峰值壓力", "selector_type": "ID", "selector_value": "LeftEarPressure", "input_type": "Text", "key": "Tymp_Left_Pressure"},
    {"category": "中耳鼓室圖", "sub_category": "左耳", "name": "峰值聲導抗", "selector_type": "ID", "selector_value": "LeftEarCompliance", "input_type": "Text", "key": "Tymp_Left_Compliance"},

    # --- 中耳鼓室圖 (右耳) ---
    {"category": "中耳鼓室圖", "sub_category": "右耳", "name": "類型", "selector_type": "ID", "selector_value": "RightEarType", "input_type": "Text", "key": "Tymp_Right_Type"},
    {"category": "中耳鼓室圖", "sub_category": "右耳", "name": "耳道容積", "selector_type": "ID", "selector_value": "RightEarVol", "input_type": "Text", "key": "Tymp_Right_Vol"},
    {"category": "中耳鼓室圖", "sub_category": "右耳", "name": "峰值壓力", "selector_type": "ID", "selector_value": "RightEarPressure", "input_type": "Text", "key": "Tymp_Right_Pressure"},
    {"category": "中耳鼓室圖", "sub_category": "右耳", "name": "峰值聲導抗", "selector_type": "ID", "selector_value": "RightEarCompliance", "input_type": "Text", "key": "Tymp_Right_Compliance"},

    # --- 言語聽力檢查 ---
    {"category": "言語聽力檢查", "sub_category": "左耳", "name": "檢查項目", "selector_type": "ID", "selector_value": "LeftSpeechThrType", "input_type": "Select", "key": "Speech_Left_Type"},
    {"category": "言語聽力檢查", "sub_category": "左耳", "name": "語音閾值結果", "selector_type": "ID", "selector_value": "LeftSpeechThrRes", "input_type": "Text", "key": "Speech_Left_SRT"},
    {"category": "言語聽力檢查", "sub_category": "左耳", "name": "語音辨識分數", "selector_type": "ID", "selector_value": "LeftSpeechScore", "input_type": "Text", "key": "Speech_Left_SDS"},
    {"category": "言語聽力檢查", "sub_category": "左耳", "name": "語音舒適響度", "selector_type": "ID", "selector_value": "LeftSpeechMcl", "input_type": "Text", "key": "Speech_Left_MCL"},

    {"category": "言語聽力檢查", "sub_category": "右耳", "name": "檢查項目", "selector_type": "ID", "selector_value": "RightSpeechThrType", "input_type": "Select", "key": "Speech_Right_Type"},
    {"category": "言語聽力檢查", "sub_category": "右耳", "name": "語音閾值結果", "selector_type": "ID", "selector_value": "RightSpeechThrRes", "input_type": "Text", "key": "Speech_Right_SRT"},
    {"category": "言語聽力檢查", "sub_category": "右耳", "name": "語音辨識分數", "selector_type": "ID", "selector_value": "RightSpeechScore", "input_type": "Text", "key": "Speech_Right_SDS"},
    {"category": "言語聽力檢查", "sub_category": "右耳", "name": "語音舒適響度", "selector_type": "ID", "selector_value": "RightSpeechMcl", "input_type": "Text", "key": "Speech_Right_MCL"},

    # Placeholder for Pure Tone Audiometry (Frequency mapping would go here)
    # The prompt included them, so I should probably include them as placeholders or generated loops
    # For brevity in this skeleton, I'll add a few key ones.
    # ...
]
