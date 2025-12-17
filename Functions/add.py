import gspread
from Functions.check_existing import check_existing_code
from datetime import datetime

def add_gift_card(sheet, code, amount, name, description):
    code = str(code).strip()

    # Get all existing codes from column A (skip header if you have one)
    if check_existing_code(sheet, code):
        print(f"❌ Gift card with code '{code}' already exists.")
        return
    
    date = datetime.now().strftime("%d.%m.%Y")

    sheet.append_row([code, date, amount, name, description], value_input_option='USER_ENTERED')

    print(f"Gift card {code} added successfully.")