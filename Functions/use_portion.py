import gspread

def use_portion(sheet, code, amount):
    # Find the row with the specified gift card code
    cell = sheet.find(code)
    if cell:
        if cell.value:
            print(f"Gift card {code} has already been used up.")
            return

        row_index = cell.row
        # Get the current amount from the gift card (assuming it's in column 3)
        current_amount = int(sheet.cell(row_index, 3).value)
        
        if amount > current_amount:
            print(f"Insufficient balance on gift card {code}. Current amount: {current_amount}, requested: {amount}")
            return
        
        # Calculate the new amount
        new_amount = current_amount - amount
        
        # Update the amount in the sheet
        sheet.update_cell(row_index, 3, new_amount)
        print(f"Used {amount} from gift card {code}. New balance: {new_amount}")
    else:
        print(f"Gift card with code {code} not found.")