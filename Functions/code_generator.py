from datetime import datetime, timedelta
import gspread
from Functions.check_existing import check_existing_code

def create_code(sheet, firstname, lastname):
    first_initial = firstname[0].upper()
    last_initial = lastname[0].upper()
    future_date = datetime.now() + timedelta(days=365)
    date_time = future_date.strftime("%d%m%y")
    code = f"CR{date_time}{first_initial}{last_initial}"

    if check_existing_code(sheet, code):
        code = f"CM{date_time}{first_initial}{last_initial}"
        if check_existing_code(sheet, code):
            code = f"CT{date_time}{first_initial}{last_initial}"
    
    return code