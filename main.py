
from setup import sheet


def main():
    first_row = sheet.row_values(1)
    print("First row:", first_row)

    sheet.update_acell("A2", "Hello from Python!")


if __name__ == "__main__":
    main()
