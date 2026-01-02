import gspread

def print_info(sheet, code):
    # Find the row with the specified gift card code
    cell = sheet.find(code)
    if cell:
        row_index = cell.row
        code = sheet.cell(row_index, 1).value
        date_added = sheet.cell(row_index, 2).value
        amount = sheet.cell(row_index, 3).value
        name = sheet.cell(row_index, 4).value
        status = sheet.cell(row_index, 5).value

        if cell.value:
            status = f"USED on {status}"
        else:
            status = "ACTIVE"

        print(f"Gift Card Info:\nCode: {code}\nDate Added: {date_added}\nAmount: {amount}\nName: {name}\nStatus: {status}")
    else:
        print(f"Gift card with code {code} not found.")