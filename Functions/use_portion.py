from datetime import datetime

def use_portion(sheet, code, amount):
    # Find the row with the specified gift card code
    cell = sheet.find(code)
    if not cell:
        print(f"Gift card with code {code} not found.")
        return

    # IMPORTANT: row index in the sheet (1-based)
    row_index = cell.row

    # Check if the gift card is already marked as USED (column 5)
    used_value = sheet.cell(row_index, 5).value
    if used_value is not None and str(used_value).strip() != "":
        print(f"Gift card {code} has already been marked as USED on {used_value}.")
        return

    # Get current balance (column 3)
    try:
        current_amount = int(sheet.cell(row_index, 3).value)
    except Exception:
        print(f"Invalid balance for gift card {code}.")
        return

    if amount > current_amount:
        print(
            f"Insufficient balance on gift card {code}. "
            f"Current amount: {current_amount}, requested: {amount}"
        )
        return

    # Calculate new balance
    new_amount = current_amount - amount
    sheet.update_cell(row_index, 3, new_amount)

    print(f"Used {amount} from gift card {code}. New balance: {new_amount}")

    # If balance becomes 0 -> mark as USED
    if new_amount == 0:
        today = datetime.today().strftime("%d.%m.%Y")
        sheet.update_cell(row_index, 5, today)
        print(f"Gift card {code} is now fully USED.")