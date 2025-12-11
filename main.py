from Functions.add import add_gift_card
from setup import sheet


def main():
    first_row = sheet.row_values(1)
    print("First row:", first_row)

    sheet.update_acell("A2", "Hello from Python!")

    add_gift_card(sheet, "GC12348", "2023-10-01", 100, "John Doe", "Gift card for John Doe")

if __name__ == "__main__":
    main()
