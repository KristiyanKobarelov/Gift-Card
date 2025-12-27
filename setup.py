import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)

client = gspread.authorize(credentials)

spreadsheet = client.open("Gift-Card-Test")  # Change after given

# Pick the specific worksheet (tab) you want to use.
# IMPORTANT: the name must match the tab name in Google Sheets EXACTLY (including spaces/case).
WORKSHEET_NAME = "Gift-Cards"

try:
    sheet = spreadsheet.worksheet(WORKSHEET_NAME)
except gspread.WorksheetNotFound:
    # Helpful debug: show available worksheet/tab names so you can copy-paste the right one.
    available = [ws.title for ws in spreadsheet.worksheets()]
    raise gspread.WorksheetNotFound(
        f"Worksheet '{WORKSHEET_NAME}' not found. Available worksheets: {available}"
    )