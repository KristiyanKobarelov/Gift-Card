from Functions.add import add_gift_card
from setup import sheet
from Functions.remove import remove_gift_card, gift_card_used

def main():
    first_row = sheet.row_values(1)
    print("First row:", first_row)

    sheet.update_acell("A2", "Hello from Python!")

    add_gift_card(sheet, "GC12348", "2023-10-01", 100, "John Doe", "Gift card for John Doe")
    remove_gift_card(sheet, "GC12348")
    gift_card_used(sheet, "GC12346")

if __name__ == "__main__":
    main()
