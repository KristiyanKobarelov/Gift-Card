import gspread
from datetime import datetime

def remove_gift_card(sheet, gift_card_code):
    # Find the row with the specified gift card code
    cell = sheet.find(gift_card_code)
    if cell:
        row_index = cell.row
        # Delete the row
        sheet.delete_rows(row_index)
        print(f"Removed gift card with code: {gift_card_code}")
    else:
        print(f"Gift card with code {gift_card_code} not found.")

def gift_card_used(sheet, gift_card_code):
    # Find the row with the specified gift card code
    cell = sheet.find(gift_card_code)
    if cell:
        row_index = cell.row
        # Mark the gift card as used by updating a specific column (e.g., column 6)

        today = datetime.today()
        formatted_date = today.strftime("%d.%m.%Y")
        sheet.update_cell(row_index, 6, formatted_date)
        print(f"Marked gift card with code {gift_card_code} as USED.")
    else:
        print(f"Gift card with code {gift_card_code} not found.")