import gspread

def add_gift_card(sheet, code, dop, amount, name, description):
    code = str(code).strip()

    # Get all existing codes from column A (skip header if you have one)
    existing_codes = [c.strip() for c in sheet.col_values(1)]  # column A

    if code in existing_codes:
        print(f"❌ Gift card with code '{code}' already exists.")
        return
    
    sheet.append_row([code, dop, amount, name, description], value_input_option='USER_ENTERED')

    print(f"Gift card {code} added successfully.")