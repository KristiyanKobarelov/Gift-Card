def check_existing_code(sheet, code):
    existing_codes = [c.strip() for c in sheet.col_values(1)]
    if code in existing_codes:
        return True
    return False