"""
Google Sheets Writer Module
Handles writing data to Google Sheets using Service Account authentication.
"""
import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False


# Credentials file path (relative to this module)
CREDENTIALS_PATH = Path(__file__).parent / "credentials.json"

# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


def is_sheets_available() -> bool:
    """Check if Google Sheets integration is available."""
    return GSPREAD_AVAILABLE and CREDENTIALS_PATH.exists()


def get_service_account_email() -> Optional[str]:
    """Get the Service Account email from credentials file."""
    if not CREDENTIALS_PATH.exists():
        return None
    
    try:
        with open(CREDENTIALS_PATH, 'r', encoding='utf-8') as f:
            creds_data = json.load(f)
            return creds_data.get('client_email')
    except Exception:
        return None


def extract_spreadsheet_id(url: str) -> Optional[str]:
    """
    Extract Spreadsheet ID from Google Sheets URL.
    
    Examples:
        https://docs.google.com/spreadsheets/d/1hAKddFdxwpTfubY0vXEEJ55_ec_5fJWB5bFYkMN0Bo8/edit
        -> 1hAKddFdxwpTfubY0vXEEJ55_ec_5fJWB5bFYkMN0Bo8
    """
    pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, url)
    return match.group(1) if match else None


def _get_client() -> Optional['gspread.Client']:
    """Get authenticated gspread client."""
    if not GSPREAD_AVAILABLE:
        print("[Sheets] gspread not installed")
        return None
    
    if not CREDENTIALS_PATH.exists():
        print(f"[Sheets] Credentials file not found: {CREDENTIALS_PATH}")
        return None
    
    try:
        creds = Credentials.from_service_account_file(
            str(CREDENTIALS_PATH),
            scopes=SCOPES
        )
        return gspread.authorize(creds)
    except Exception as e:
        print(f"[Sheets] Auth error: {e}")
        return None


def list_worksheets(spreadsheet_id: str) -> List[str]:
    """
    List all worksheet names in a spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the Google Spreadsheet
    
    Returns:
        List of worksheet names, or empty list on error
    """
    client = _get_client()
    if not client:
        return []
    
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        return [ws.title for ws in spreadsheet.worksheets()]
    except Exception as e:
        print(f"[Sheets] Error listing worksheets: {e}")
        return []


def get_spreadsheet_name(spreadsheet_id: str) -> Optional[str]:
    """
    Get the title of the spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the Google Spreadsheet
    
    Returns:
        The title of the spreadsheet, or None if error
    """
    client = _get_client()
    if not client:
        return None
    
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        return spreadsheet.title
    except Exception as e:
        print(f"[Sheets] Error getting spreadsheet name: {e}")
        return None


def append_row_to_sheet(spreadsheet_id: str, row_data: List[Any], sheet_name: str = "來客紀錄") -> bool:
    """
    Append a row of data to a Google Sheet at the next row after the last entry in column A.
    
    Args:
        spreadsheet_id: The ID of the Google Spreadsheet
        row_data: List of values to append as a new row
        sheet_name: Name of the worksheet (default: '來客紀錄')
    
    Returns:
        True if successful, False otherwise
    """
    client = _get_client()
    if not client:
        return False
    
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Find worksheet by name
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            print(f"[Sheets] Worksheet '{sheet_name}' not found")
            return False
        
        # Get last row number from column A to find where to insert
        col_a_values = worksheet.col_values(1)  # Get all values in column A
        
        # Find the actual last row with data in column A (count non-empty cells)
        last_row_index = len(col_a_values)  # This is the last row with data (1-indexed equivalent)
        
        # Find the last numeric value in column A for the sequence number
        last_row_num = 0
        for val in reversed(col_a_values):
            try:
                last_row_num = int(val)
                break
            except (ValueError, TypeError):
                continue
        
        # Set the new row number in column A
        row_data[0] = last_row_num + 1
        
        # Calculate the target row (next row after the last entry in column A)
        target_row = last_row_index + 1
        
        # Filter out None values to preserve formulas in those columns
        # Build a list of (column_letter, value) pairs for non-None values
        updates = []
        for col_index, value in enumerate(row_data):
            if value is not None:  # Only write non-None values
                # Convert column index to letter (0=A, 1=B, etc.)
                col_letter = chr(ord('A') + col_index) if col_index < 26 else \
                             chr(ord('A') + col_index // 26 - 1) + chr(ord('A') + col_index % 26)
                cell_ref = f"{col_letter}{target_row}"
                updates.append({
                    'range': cell_ref,
                    'values': [[value]]
                })
        
        # Batch update all cells at once
        if updates:
            worksheet.batch_update(updates, value_input_option='USER_ENTERED')
        
        print(f"[Sheets] Successfully wrote row {last_row_num + 1} to '{sheet_name}' at row {target_row}")
        return True
        
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"[Sheets] Spreadsheet not found: {spreadsheet_id}")
        return False
    except gspread.exceptions.APIError as e:
        print(f"[Sheets] API Error: {e}")
        return False
    except Exception as e:
        print(f"[Sheets] Error: {e}")
        return False


def calculate_pta(
    freq_500: Optional[float],
    freq_1000: Optional[float],
    freq_2000: Optional[float],
    freq_4000: Optional[float]
) -> Optional[float]:
    """
    Calculate Pure Tone Average (PTA) from air conduction thresholds.
    
    Formula: (500Hz + 1000Hz + 2000Hz + 4000Hz) / 4
    
    Returns None if any required frequency is missing.
    """
    values = [freq_500, freq_1000, freq_2000, freq_4000]
    valid_values = [v for v in values if v is not None]
    
    if len(valid_values) < 4:
        # If we have at least 3 values, calculate average of available
        if len(valid_values) >= 3:
            return round(sum(valid_values) / len(valid_values), 2)
        return None
    
    return round(sum(valid_values) / 4, 2)


def build_row_data(
    inspector_name: str,
    test_date: str,
    patient_name: str,
    birth_date: str,
    phone: str,
    customer_source: str,
    clinic_name: str,
    has_invitation_card: str,
    store_code: str,
    recommend_id: str,
    voucher_count: str,
    voucher_id: str,
    is_deal: str,
    transaction_amount: str,
    right_pta: Optional[float],
    left_pta: Optional[float]
) -> List[Any]:
    """
    Build the row data array for Google Sheets.
    
    Column mapping (A-AC):
    A: 流水號 (auto-increment)
    B: 主聽力師
    C: 服務日期 (format: 2026/1/7)
    D: 顧客姓名
    E: 顧客生日
    F: 年齡 (FORMULA - DO NOT FILL)
    G: 電話
    H: 顧客來源 (multi-select, comma separated)
    I: 診所名稱
    J: 有無邀請卡
    K: 門市編號 (only if has invitation card)
    L: 門市名稱 (FORMULA - DO NOT FILL)
    M: 推薦人工號 (only if has invitation card)
    N: 員工姓名 (FORMULA - DO NOT FILL)
    O-Q: FALSE (checkboxes)
    R: 金鑽券發放張數 (only if has invitation card)
    S: 金鑽券發放編號 (only if has invitation card)
    T: 是否成交
    U: 成交金額 (only if is_deal is "是")
    V: 右耳 PTA
    W: 右耳聽損程度 (FORMULA - DO NOT FILL)
    X: 左耳 PTA
    Y: 左耳聽損程度 (FORMULA - DO NOT FILL)
    Z: 是否不對稱聽損 (FORMULA - DO NOT FILL)
    AA-AC: Empty (後續填寫)
    
    IMPORTANT: Use None for formula columns - they will be skipped during write.
    """
    # Format date from ISO format (2026-01-07) to display format (2026/1/7)
    formatted_date = ""
    if test_date:
        try:
            parts = test_date.split("-")
            if len(parts) == 3:
                year, month, day = parts
                formatted_date = f"{year}/{int(month)}/{int(day)}"
        except:
            formatted_date = test_date  # fallback to original
    
    return [
        "",                     # A: Empty (流水號 - will be set by append function)
        inspector_name,         # B: 主聽力師
        formatted_date,         # C: 服務日期 (formatted)
        patient_name,           # D: 顧客姓名
        birth_date,             # E: 顧客生日
        None,                   # F: SKIP (年齡 formula)
        phone,                  # G: 電話
        customer_source,        # H: 顧客來源 (comma separated for multi-select)
        clinic_name,            # I: 診所名稱
        has_invitation_card,    # J: 有無邀請卡
        store_code,             # K: 門市編號
        None,                   # L: SKIP (門市 formula)
        recommend_id,           # M: 推薦人工號
        None,                   # N: SKIP (員工姓名 formula)
        False,                  # O: google評論
        False,                  # P: 官方Line
        False,                  # Q: 送口罩
        voucher_count,          # R: 金鑽券發放張數
        voucher_id,             # S: 金鑽券發放編號
        is_deal,                # T: 是否成交
        transaction_amount,     # U: 成交金額
        right_pta if right_pta is not None else "",  # V: 右耳 PTA
        None,                   # W: SKIP (右耳聽損程度 formula)
        left_pta if left_pta is not None else "",    # X: 左耳 PTA
        None,                   # Y: SKIP (左耳聽損程度 formula)
        None,                   # Z: SKIP (是否不對稱聽損 formula)
        "",                     # AA: Empty (是否有借機)
        "",                     # AB: Empty (報價反映)
        "",                     # AC: Empty (後續追蹤)
    ]


# Test function
if __name__ == "__main__":
    print(f"Sheets Available: {is_sheets_available()}")
    print(f"Service Account Email: {get_service_account_email()}")
    
    test_url = "https://docs.google.com/spreadsheets/d/1hAKddFdxwpTfubY0vXEEJ55_ec_5fJWB5bFYkMN0Bo8/edit"
    print(f"Extracted ID: {extract_spreadsheet_id(test_url)}")
